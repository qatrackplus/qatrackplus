"""The repair that puts back unique constraints the database stopped enforcing.

These run on whatever engine the suite is using. That is possible *because* the repair
names no engine: its decisions come from introspecting the database in front of it, so
the decision logic can be asserted anywhere. An earlier version guarded on
`connection.vendor == 'microsoft'`, and nothing about it could be tested except on SQL
Server.
"""

from unittest import skipUnless

from django.apps import apps
from django.db import connection
from django.db.models import Q
from django.test import TestCase, TransactionTestCase

from qatrack.parts.models import Contact, Room
from qatrack.qa.models import TestListInstance
from qatrack.qatrack_core.unique_repair import (
    _build,
    constraint_name,
    nullable_fields,
    remove_repaired_constraints,
    repair_unique_constraints,
)

SPECS = [
    ('parts', 'Contact', ('first_name', 'last_name', 'supplier')),
    ('parts', 'Room', ('name', 'site')),
    ('qa', 'TestListInstance', ('user_key',)),
]


class TestConstraintName(TestCase):

    def test_it_is_deterministic(self):
        """Idempotence and reversal both depend on this."""
        a = constraint_name(Contact, ('first_name', 'last_name', 'supplier'))
        b = constraint_name(Contact, ('first_name', 'last_name', 'supplier'))
        assert a == b

    def test_different_fields_give_different_names(self):
        assert constraint_name(Contact, ('first_name',)) != constraint_name(Contact, ('last_name',))

    def test_different_models_give_different_names(self):
        """The hash covers the table, so two models sharing a field list do not collide."""
        assert constraint_name(Contact, ('name',)) != constraint_name(Room, ('name',))

    def test_it_fits_every_backend_identifier_limit(self):
        """SQL Server allows 128; the shortest limit among supported backends is 30."""
        for model, fields in [
            (Contact, ('first_name', 'last_name', 'supplier')),
            (TestListInstance, ('user_key',)),
        ]:
            name = constraint_name(model, fields)
            assert len(name) <= 63, (name, len(name))


class TestBuiltConstraint(TestCase):

    def test_no_condition_when_nothing_is_nullable(self):
        c = _build(Contact, ('first_name', 'last_name', 'supplier'))
        assert c.condition is None

    def test_nullable_columns_produce_a_filtered_constraint(self):
        """Django permits many NULLs in a nullable unique column; SQL Server does not.

        Without the condition the restored index would reject a second NULL row that the
        application considers valid, so the filter is what makes the repair match
        Django's semantics rather than the engine's.
        """
        c = _build(Room, ('name', 'site'))
        assert c.condition == Q(site__isnull=False)

    def test_every_nullable_column_appears_in_the_condition(self):
        c = _build(
            apps.get_model('service_log', 'Hours'),
            ('service_event', 'third_party', 'user'),
            ('third_party', 'user'),
        )
        assert c.condition == Q(third_party__isnull=False, user__isnull=False)


class TestRepairDecisions(TransactionTestCase):
    """`TransactionTestCase`, not `TestCase`.

    These open a schema editor, and SQLite refuses to do that inside an atomic block -
    which is what `TestCase` wraps every test in.

    `tearDown` undoes any constraint the repair created, because on an engine that is
    genuinely missing them the repair issues real DDL - and the first version of this
    class leaked a constraint from one test into the next on SQL Server.

    **Removal is by generated name, and that is not enough on its own.** The repair
    migrations generate the *same* names, so once they have run during test-database
    setup those constraints are indistinguishable by name from ones a test created -
    and a blanket removal in `tearDown` would delete real migrated schema, leaving
    every later test running against a database that no longer enforces it. Both
    reviewers caught this on c#5.

    So `setUp` records which of the generated names are already present, and `tearDown`
    removes only the ones that were not. A constraint the database or a migration owns
    is left alone whether or not it shares our naming.
    """

    def _generated_names_present(self):
        """Which of SPECS' generated constraint names exist right now."""
        present = set()
        for app_label, model_name, fields in SPECS:
            model = apps.get_model(app_label, model_name)
            name = constraint_name(model, fields)
            with connection.cursor() as cursor:
                existing = connection.introspection.get_constraints(
                    cursor, model._meta.db_table
                )
            if name in existing:
                present.add(name)
        return present

    def setUp(self):
        super().setUp()
        self.preexisting_constraint_names = self._generated_names_present()

    def tearDown(self):
        ours = [
            spec for spec in SPECS
            if constraint_name(apps.get_model(spec[0], spec[1]), spec[2])
            not in self.preexisting_constraint_names
        ]
        if ours:
            with connection.schema_editor() as editor:
                remove_repaired_constraints(apps, editor, ours)
        super().tearDown()

    def _own_specs_present(self, specs):
        """Which of `specs` currently carry this module's generated name."""
        present = self._generated_names_present()
        return [
            spec for spec in specs
            if constraint_name(apps.get_model(spec[0], spec[1]), spec[2]) in present
        ]

    def _ensure_absent(self, specs=SPECS):
        """Clear this module's own names, and report what was cleared so it can go back.

        **Three tests need this and none of them used to have it.** The repair
        migrations generate the same names, so on SQL Server - where the 4.0 retype
        dropped the indexes and 4.0.2 re-created them - every one of SPECS already
        carries its generated name before any test runs. A test that assumes
        otherwise either removes migrated schema or collides with it.

        Pair every call with `_restore`, because the class's whole invariant is that a
        constraint a migration owns is never left deleted (see the class docstring).
        """
        removed = self._own_specs_present(specs)
        if removed:
            with connection.schema_editor() as editor:
                remove_repaired_constraints(apps, editor, removed)
        return removed

    def _restore(self, specs):
        """Put back exactly what `_ensure_absent` cleared, the way a migration made it."""
        if specs:
            with connection.schema_editor() as editor:
                repair_unique_constraints(apps, editor, specs)

    @skipUnless(
        connection.features.supports_partial_indexes,
        "needs a constraint that introspects under its own name; see the note below",
    )
    def test_teardown_leaves_a_constraint_that_was_there_at_setup(self):
        """The guard itself, asserted rather than assumed.

        Skipped where partial indexes are unsupported, which is MySQL. The
        constraint has to come back from `get_constraints` under the name it was
        given, and only a *conditional* UniqueConstraint does: Django renders
        that as `CREATE UNIQUE INDEX ... WHERE ...`, keeping the name, while an
        unconditional one is a table-level UNIQUE clause whose name introspection
        does not return on SQLite. On MySQL the conditional form is silently
        skipped instead. Either way the name is absent for reasons that have
        nothing to do with the snapshot filter this test is about, so the honest
        move is to skip rather than to weaken the assertion.

        Creates a constraint under a generated name *before* `setUp`'s snapshot would
        have seen it, by snapshotting again afterwards, and checks `tearDown`'s filter
        would exclude it. Without the snapshot this class deletes migrated schema.
        """
        room = [('parts', 'Room', ('name', 'site'))]
        # Run alone on SQL Server, this used to fail with "an index or statistics with
        # name 'qatrack_uniq_parts_room_0d1952b2' already exists": the repair migration
        # had already created it, and `add_constraint` below collided. It only passed in
        # a full run because unittest sorts methods alphabetically and
        # `test_repair_then_reverse...` had removed that index first. Verified on
        # pristine `42783309` against SQL Server 2022.
        cleared = self._ensure_absent(room)
        model = apps.get_model('parts', 'Room')
        name = constraint_name(model, ('name', 'site'))
        with connection.schema_editor() as editor:
            editor.add_constraint(model, _build(model, ('name', 'site')))
        try:
            assert name in self._generated_names_present()
            self.preexisting_constraint_names = self._generated_names_present()
            survivors = [
                spec for spec in SPECS
                if constraint_name(apps.get_model(spec[0], spec[1]), spec[2])
                not in self.preexisting_constraint_names
            ]
            assert all(constraint_name(apps.get_model(s[0], s[1]), s[2]) != name
                       for s in survivors), survivors
        finally:
            with connection.schema_editor() as editor:
                editor.remove_constraint(model, _build(model, ('name', 'site')))
            self._restore(cleared)


    def test_it_does_nothing_where_the_database_already_enforces(self):
        """The whole basis for having no engine guard.

        On SQLite, PostgreSQL and MySQL every declared constraint is enforced, so every
        spec is skipped and no DDL is issued. This is the assertion that replaced
        `if connection.vendor != 'microsoft': return` - it tests the real condition
        rather than a proxy for it.
        """
        with connection.schema_editor() as editor:
            result = repair_unique_constraints(apps, editor, SPECS)

        if any(c in connection.vendor for c in ('sqlite', 'postgresql', 'mysql')):
            assert result['created'] == [], result
            assert len(result['already_enforced']) == len(SPECS), result
            assert result['blocked'] == [] and result['unsupported'] == [], result
        else:
            # An engine that may legitimately be missing them; every spec must still be
            # accounted for exactly once.
            total = sum(len(result[k]) for k in ('created', 'already_enforced', 'blocked', 'unsupported'))
            assert total == len(SPECS), result

    def test_a_partial_index_is_refused_where_unsupported_rather_than_emitted(self):
        """MySQL cannot express one, and must be told rather than left looking repaired.

        **This used to prove nothing.** It skipped on every engine that supports partial
        indexes - which is the one the suite normally runs on - and where it did run it
        accepted `already_enforced` *or* `unsupported`, so a database that already
        enforced everything passed it without the branch under test ever executing.
        Caught by @coderabbitai on c#5.

        Both conditions are now forced, so it runs everywhere and can only pass by
        reaching the branch: the engine is told it has no partial index support, and the
        constraints are reported as not enforced.
        """
        from unittest import mock

        # Asked of the model, as the repair itself now does, rather than read
        # from a fourth element the specs no longer carry.
        nullable_specs = [
            s for s in SPECS
            if nullable_fields(apps.get_model(s[0], s[1]), s[2])
        ]
        assert nullable_specs, "SPECS no longer has a nullable spec to exercise"

        with mock.patch.object(
            type(connection.features), 'supports_partial_indexes', False
        ), mock.patch(
            'qatrack.qatrack_core.unique_repair._is_enforced', return_value=False
        ):
            with connection.schema_editor() as editor:
                result = repair_unique_constraints(apps, editor, nullable_specs)

        for spec in nullable_specs:
            label = "%s.%s %s" % (spec[0], spec[1], list(spec[2]))
            assert label in result['unsupported'], (label, result)
        assert not result['created'], result

    def test_reversal_leaves_constraints_it_did_not_create(self):
        """It removes by generated name, so the database's own indexes are untouched.

        Asserted from a state where none of this module's names are present, so every
        unique constraint left on the table is one the database owns. Reversal must be
        a no-op in that situation, on every engine.

        The state is established rather than assumed. It used to be assumed, and on
        SQL Server the assumption was false: the repair migration had already created
        those names, so this removed migrated schema and passed only because the
        column set had already been taken away by the test that sorts before it.
        """
        cleared = self._ensure_absent()
        try:
            before = self._unique_sets(Contact)
            with connection.schema_editor() as editor:
                remove_repaired_constraints(apps, editor, SPECS)
            assert self._unique_sets(Contact) == before
        finally:
            self._restore(cleared)

    def test_repair_then_reverse_returns_the_schema_to_where_it_started(self):
        """The round trip, over a state in which this call is the one that creates.

        **This is the test that failed on SQL Server 2019, 2022 and 2025** - measured
        by crane on all three, reproduced here on 2022, and the one red job on c#24.

        It asserted identity from whatever the migrations had left behind. On SQL
        Server that is `qatrack_uniq_parts_contact_b0a03600` on
        `(first_name, last_name, supplier_id)`, created by the 4.0.2 repair migration
        because the 4.0 retype dropped it. So the forward pass reported
        `already_enforced` and created nothing, while the reverse removed the
        migration's index by name - leaving `parts_contact` with only its primary key,
        which is the `assert {frozenset({'id'})} == ...` CI reported.

        **Nothing about the repair is wrong there.** Reversal removes the names this
        module owns, which is right for its only caller - a migration undoing its own
        forward pass. Only a second forward pass sees the difference, and nothing but
        this test does that.

        Clearing those names first makes the round trip this call's own. It also makes
        the assertion mean something on an engine that is already fully enforced:
        with them gone, the forward pass has something to create.
        """
        cleared = self._ensure_absent()
        try:
            before = self._unique_sets(Contact)
            with connection.schema_editor() as editor:
                result = repair_unique_constraints(apps, editor, SPECS)
            if result['created']:
                # Not vacuous: the clear above gave the forward pass real work, so the
                # removal that follows is removing something this call created.
                assert self._unique_sets(Contact) != before, result
            with connection.schema_editor() as editor:
                remove_repaired_constraints(apps, editor, SPECS)
            assert self._unique_sets(Contact) == before
        finally:
            self._restore(cleared)

    def _unique_sets(self, model):
        with connection.cursor() as cursor:
            cons = connection.introspection.get_constraints(cursor, model._meta.db_table)
        return {frozenset(d['columns']) for d in cons.values() if d.get('unique') and d.get('columns')}
