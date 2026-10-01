"""The database is not always enforcing what the models declare.

mssql-django drops a unique index when an unrelated AlterField retypes a
model's primary key, which the 4.0 migrations do to every model, and never
recreates it. Nothing complains: the ORM simply stops raising IntegrityError.
Confirmed against mssql-django 1.7.3, 1.8.0 and 2.0.0; PostgreSQL and SQLite
are unaffected.

These tests run on whatever engine the suite is using, so the ones that need a
missing constraint fake it rather than requiring SQL Server.
"""

from unittest import mock

from django.core.checks import Warning as CheckWarning
from django.db import connection
from django.test import TestCase

from qatrack.qa.models import TestListInstance
from qatrack.qatrack_core.checks import (
    check_unique_constraints_enforced,
    declared_unique_columns,
    enforced_unique_columns,
    unenforced_unique_columns,
)


class TestDeclaredUniqueColumns(TestCase):

    def test_single_unique_field(self):
        declared = declared_unique_columns(TestListInstance)
        assert frozenset(['user_key']) in declared

    def test_primary_key_is_excluded(self):
        # It is unique by construction, and a missing one fails far louder.
        declared = declared_unique_columns(TestListInstance)
        assert frozenset(['id']) not in declared

    def test_unique_together_is_included_as_one_set(self):
        from qatrack.parts.models import Part

        declared = declared_unique_columns(Part)
        assert frozenset(['part_number', 'new_or_used']) in declared

    def test_order_does_not_matter(self):
        # Uniqueness over (a, b) is the same guarantee as over (b, a), and
        # introspection reports whatever order the index used.
        from qatrack.parts.models import Part

        declared = declared_unique_columns(Part)
        assert frozenset(['new_or_used', 'part_number']) in declared

    def test_conditional_constraints_are_skipped(self):
        """A partial index is a different question and this check does not ask it."""
        from django.db.models import Q, UniqueConstraint

        constraint = UniqueConstraint(fields=['user_key'], name='x', condition=Q(in_progress=True))
        with mock.patch.object(TestListInstance._meta, 'constraints', [constraint]):
            declared = declared_unique_columns(TestListInstance)
        # user_key is still there from the field itself, but no extra entry
        # was added for the conditional constraint.
        assert declared == {frozenset(['user_key'])}


class TestUnenforcedComparison(TestCase):

    def test_nothing_missing(self):
        both = {frozenset(['a']), frozenset(['b', 'c'])}
        assert unenforced_unique_columns(both, both) == []

    def test_missing_one(self):
        declared = {frozenset(['a']), frozenset(['b'])}
        enforced = {frozenset(['a'])}
        assert unenforced_unique_columns(declared, enforced) == [['b']]

    def test_a_wider_constraint_does_not_satisfy_a_narrower_one(self):
        # Unique over (a, b) permits duplicate a values, so this must be a set
        # difference and not a subset test.
        declared = {frozenset(['a'])}
        enforced = {frozenset(['a', 'b'])}
        assert unenforced_unique_columns(declared, enforced) == [['a']]

    def test_output_is_deterministic(self):
        declared = {frozenset(['z']), frozenset(['b', 'a']), frozenset(['m'])}
        assert unenforced_unique_columns(declared, set()) == [['m'], ['z'], ['a', 'b']]


class TestCheckBehaviour(TestCase):

    def test_no_database_work_without_the_databases_kwarg(self):
        """Registered under Tags.database, so ordinary commands must skip it."""
        assert check_unique_constraints_enforced(None, databases=None) == []
        assert check_unique_constraints_enforced(None) == []

    def test_the_check_produces_no_false_positives(self):
        """Everything the check reports is genuinely not enforced.

        On SQLite, PostgreSQL and MySQL that means silence, because those engines
        enforce what they are told.

        **On SQL Server it may legitimately report findings, and that is not a false
        positive** - it is the defect this check exists to surface. CI's own Windows
        SQL Server test database has all sixteen of them. So the assertion there is
        that each finding is real, checked against the connection's own introspection,
        rather than that there are none.

        The obvious version of this test, `== []`, passes on three engines and fails on
        the fourth for being right. It did exactly that in CI before this was fixed.

        Worth being clear about what the SQL Server branch is worth: it re-runs the same
        comparison the check itself used, so it catches a check that reports a model
        whose constraints are all enforced, and little else. The strong assertions about
        SQL Server's behaviour are not here - they cannot be, because this suite has to
        run on whatever engine CI gives it.
        """
        problems = check_unique_constraints_enforced(None, databases=['default'])

        if connection.vendor != 'microsoft':
            assert problems == [], (
                "%s enforces what it is told, so the check should be silent: %r"
                % (connection.vendor, [p.msg for p in problems])
            )
            return

        for problem in problems:
            model = problem.obj
            missing = unenforced_unique_columns(
                declared_unique_columns(model),
                enforced_unique_columns(connection, model._meta.db_table),
            )
            assert missing, (
                "%s was reported, but the database enforces every set it declares"
                % model._meta.label
            )

    def test_a_missing_constraint_is_reported(self):
        with mock.patch(
            'qatrack.qatrack_core.checks.enforced_unique_columns', return_value=set()
        ):
            problems = check_unique_constraints_enforced(None, databases=['default'])

        assert problems, "a database enforcing nothing should produce findings"
        assert all(isinstance(p, CheckWarning) for p in problems), "must not be an Error"
        assert all(p.id == 'qatrack.W011' for p in problems)

    def test_it_is_a_warning_not_an_error(self):
        """Checks run before migrate; an Error would abort the fix."""
        with mock.patch(
            'qatrack.qatrack_core.checks.enforced_unique_columns', return_value=set()
        ):
            problems = check_unique_constraints_enforced(None, databases=['default'])
        assert not any(p.is_serious() for p in problems)

    def test_the_hint_gives_runnable_sql(self):
        with mock.patch(
            'qatrack.qatrack_core.checks.enforced_unique_columns', return_value=set()
        ):
            problems = check_unique_constraints_enforced(None, databases=['default'])
        hints = [p.hint for p in problems]
        assert any('CREATE UNIQUE INDEX' in h for h in hints)
        # The hint must say the migrations do this, not only offer the manual SQL.
        # crane watched an upgrade print 16 "recreate it by hand" instructions and then
        # watched the same `migrate` create them - system checks run before migrations,
        # so an admin reads the warning and the fix in the wrong order.
        assert any('4.0.2 migrations re-create these' in h for h in hints)
        assert any('check_unique_constraints' in h for h in hints)
        assert any('IS NOT NULL' in h for h in hints), "SQL Server treats NULLs as equal"

    def test_an_unreachable_database_is_not_this_checks_problem(self):
        from django.db.utils import DatabaseError

        with mock.patch.object(
            connection.introspection, 'table_names', side_effect=DatabaseError('nope')
        ):
            assert check_unique_constraints_enforced(None, databases=['default']) == []

    def test_tables_that_do_not_exist_yet_are_skipped(self):
        """First migrate on an empty database must not produce noise."""
        with mock.patch.object(connection.introspection, 'table_names', return_value=[]):
            assert check_unique_constraints_enforced(None, databases=['default']) == []


class TestIntrospectionAgreesWithThisEngine(TestCase):

    def test_enforced_columns_can_read_a_unique_index_at_all(self):
        """Guards against the introspection shape changing under us.

        Asserted across the schema rather than on one table. A single table is the wrong
        unit: on SQL Server any given constraint may legitimately be absent, and the
        primary key is no use either - SQLite reports it with `unique=False`, so it is
        not in this function's output on every engine.

        What is true everywhere is that *some* declared unique constraint is enforced.
        If `enforced_unique_columns` stopped reading them - a changed introspection
        shape, a renamed key in the dict - none would be found anywhere, and every
        model would look broken rather than one.
        """
        from django.apps import apps

        found = 0
        for model in apps.get_models():
            if not model._meta.managed:
                continue
            declared = declared_unique_columns(model)
            if not declared:
                continue
            try:
                enforced = enforced_unique_columns(connection, model._meta.db_table)
            except Exception:  # noqa: BLE001 - a table this engine lacks is not the point
                continue
            found += len(declared & enforced)

        assert found, (
            "introspection found no enforced unique constraint anywhere on %s, so "
            "enforced_unique_columns is not reading them" % connection.vendor
        )

    def test_user_key_is_enforced_except_where_sql_server_dropped_it(self):
        """`TestListInstance.user_key` keeps API submissions unique.

        It is the constraint this whole check exists for, so it is worth asserting
        directly - but **on SQL Server it is legitimately absent until the repair
        migration runs**, which is the defect, not a test failure. An earlier version of
        this asserted it unconditionally and failed on CI's mssql job for being right.
        """
        enforced = enforced_unique_columns(connection, TestListInstance._meta.db_table)
        present = frozenset(['user_key']) in enforced

        if connection.vendor != 'microsoft':
            assert present, (
                "%s should enforce user_key; if it does not, the problem is wider than "
                "SQL Server" % connection.vendor
            )
        elif not present:
            # Expected on an unrepaired SQL Server database. Assert the check agrees,
            # so a silent change in either direction is still caught.
            missing = unenforced_unique_columns(
                declared_unique_columns(TestListInstance), enforced
            )
            assert ['user_key'] in missing, (
                "user_key is not enforced but the check does not report it: %r" % missing
            )
