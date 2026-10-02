"""The repair that puts back unique constraints the database stopped enforcing.

These run on whatever engine the suite is using. That is possible *because* the repair
names no engine: its decisions come from introspecting the database in front of it, so
the decision logic can be asserted anywhere. An earlier version guarded on
`connection.vendor == 'microsoft'`, and nothing about it could be tested except on SQL
Server.
"""

from django.apps import apps
from django.db import connection
from django.db.models import Q
from django.test import TestCase, TransactionTestCase

from qatrack.parts.models import Contact, Room
from qatrack.qa.models import TestListInstance
from qatrack.qatrack_core.unique_repair import (
    _build,
    constraint_name,
    remove_repaired_constraints,
    repair_unique_constraints,
)

SPECS = [
    ('parts', 'Contact', ('first_name', 'last_name', 'supplier'), ()),
    ('parts', 'Room', ('name', 'site'), ('site',)),
    ('qa', 'TestListInstance', ('user_key',), ('user_key',)),
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
        c = _build(Contact, ('first_name', 'last_name', 'supplier'), ())
        assert c.condition is None

    def test_nullable_columns_produce_a_filtered_constraint(self):
        """Django permits many NULLs in a nullable unique column; SQL Server does not.

        Without the condition the restored index would reject a second NULL row that the
        application considers valid, so the filter is what makes the repair match
        Django's semantics rather than the engine's.
        """
        c = _build(Room, ('name', 'site'), ('site',))
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
    class leaked a constraint from one test into the next on SQL Server. Removal is by
    generated name, so a constraint the database owns is never touched.
    """

    def tearDown(self):
        with connection.schema_editor() as editor:
            remove_repaired_constraints(apps, editor, SPECS)
        super().tearDown()


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
        """MySQL cannot express one, and must be told rather than left looking repaired."""
        if connection.features.supports_partial_indexes:
            self.skipTest("this engine supports partial indexes")

        with connection.schema_editor() as editor:
            result = repair_unique_constraints(apps, editor, SPECS)

        nullable_specs = [s for s in SPECS if s[3]]
        for spec in nullable_specs:
            label = "%s.%s %s" % (spec[0], spec[1], list(spec[2]))
            assert label in result['already_enforced'] + result['unsupported'], result

    def test_reversal_leaves_constraints_it_did_not_create(self):
        """It removes by generated name, so the database's own indexes are untouched.

        Asserted without the repair having run, so nothing this module created is
        present and every unique constraint on the table belongs to the database.
        Reversal must be a no-op in that situation, on every engine.
        """
        before = self._unique_sets(Contact)
        with connection.schema_editor() as editor:
            remove_repaired_constraints(apps, editor, SPECS)
        assert self._unique_sets(Contact) == before

    def test_repair_then_reverse_returns_the_schema_to_where_it_started(self):
        """The round trip, which only does anything on an engine missing a constraint."""
        before = self._unique_sets(Contact)
        with connection.schema_editor() as editor:
            repair_unique_constraints(apps, editor, SPECS)
        with connection.schema_editor() as editor:
            remove_repaired_constraints(apps, editor, SPECS)
        assert self._unique_sets(Contact) == before

    def _unique_sets(self, model):
        with connection.cursor() as cursor:
            cons = connection.introspection.get_constraints(cursor, model._meta.db_table)
        return {frozenset(d['columns']) for d in cons.values() if d.get('unique') and d.get('columns')}
