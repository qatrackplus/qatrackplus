"""`manage.py check_unique_constraints`, driven through `call_command`.

The command had no command-level coverage at all: its database routing, its summaries
and its exit messages were unverified, which @coderabbitai pointed out on c#5 while
noting that `test_sample_data.py` exercises the other core command exactly this way.

What each test here is actually guarding is the *wording of the verdict*, because this
command exists to be believed. "Nothing to repair" after failing to read half the
tables, or after finding duplicates behind an index that claims to prevent them, is
worse than no command at all - a site would walk into the repair migration confident.
"""

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.db import DEFAULT_DB_ALIAS, connection
from django.test import TestCase, TransactionTestCase

from qatrack.qatrack_core.management.commands.check_unique_constraints import (
    Command,
    duplicate_groups,
    summarise_groups,
)


def run(**kwargs):
    out = StringIO()
    call_command("check_unique_constraints", stdout=out, stderr=out, **kwargs)
    return out.getvalue()


class TestHealthyDatabase(TestCase):
    """A database with nothing to repair - simulated, not assumed.

    On SQL Server the test database genuinely *is* missing constraints, because
    that is the defect this command exists to report: a fresh 4.0 schema there
    has 16 unenforced column sets, and the command correctly says so. A test that
    asserted "Nothing to repair" against the live scan therefore passed on SQLite
    and PostgreSQL and failed on the one engine the command is for.

    So the clean verdict is tested by making the scan clean, which is also closer
    to what these tests are for: the wording, not the schema.
    """

    def test_it_names_the_database_and_vendor(self):
        output = run()
        assert "Database: %s" % DEFAULT_DB_ALIAS in output
        assert connection.vendor in output

    def test_a_clean_run_says_so_unambiguously(self):
        from qatrack.qatrack_core.management.commands import check_unique_constraints as cmd

        with mock.patch.object(cmd, 'unenforced_unique_columns', return_value=[]):
            output = run()
        assert "Nothing to repair" in output, output
        assert "Inconclusive" not in output

    def test_an_unhealthy_database_does_not_say_nothing_to_repair(self):
        """The negative control, and the case SQL Server actually produces."""
        from qatrack.qatrack_core.management.commands import check_unique_constraints as cmd

        def report_the_first_set(declared, enforced):
            return [tuple(sorted(next(iter(declared))))] if declared else []

        with mock.patch.object(cmd, 'unenforced_unique_columns', side_effect=report_the_first_set):
            output = run()
        assert "Nothing to repair" not in output, output
        assert "not enforced" in output

    def test_it_counts_the_models_it_checked(self):
        output = run()
        assert "models declare uniqueness" in output


class TestIntrospectionFailure(TestCase):
    """A failure to look must never read as a clean result."""

    def test_it_reports_inconclusive_rather_than_success(self):
        with mock.patch(
            "qatrack.qatrack_core.management.commands.check_unique_constraints"
            ".enforced_unique_columns",
            side_effect=Exception("no such table"),
        ):
            output = run()
        assert "Inconclusive" in output, output
        assert "could not be introspected" in output
        assert "every declared unique constraint is enforced" not in output

    def test_it_still_names_the_models_it_could_not_read(self):
        with mock.patch(
            "qatrack.qatrack_core.management.commands.check_unique_constraints"
            ".enforced_unique_columns",
            side_effect=Exception("no such table"),
        ):
            output = run()
        assert "could not introspect" in output


class TestDatabaseAliasIsUsedForRows(TestCase):
    """Schema from one database and rows from another is the failure mode here."""

    def test_the_alias_reaches_the_duplicate_query(self):
        with mock.patch(
            "qatrack.qatrack_core.management.commands.check_unique_constraints"
            ".enforced_unique_columns",
            return_value=set(),
        ), mock.patch(
            "qatrack.qatrack_core.management.commands.check_unique_constraints"
            ".duplicate_groups",
            wraps=duplicate_groups,
        ) as dupes:
            run(database=DEFAULT_DB_ALIAS)
        assert dupes.call_args_list, "no column set was examined, so this proves nothing"
        for call in dupes.call_args_list:
            assert call.kwargs.get("using") == DEFAULT_DB_ALIAS, call

    def test_duplicate_groups_respects_using(self):
        from qatrack.parts.models import Room

        qs = duplicate_groups(Room, ["name", "site"], using=DEFAULT_DB_ALIAS)
        assert qs.db == DEFAULT_DB_ALIAS


class TestLimitBoundsMemoryNotJustOutput(TestCase):

    def test_only_limit_groups_are_retained(self):
        groups = [{"num": n} for n in range(10, 0, -1)]

        class FakeQS:
            def iterator(self):
                return iter(groups)

        kept, total, excess = summarise_groups(FakeQS(), 3)
        assert len(kept) == 3, kept
        assert total == 10
        assert excess == sum(g["num"] - 1 for g in groups)

    def test_counts_are_complete_even_though_output_is_not(self):
        groups = [{"num": 2}] * 100

        class FakeQS:
            def iterator(self):
                return iter(groups)

        kept, total, excess = summarise_groups(FakeQS(), 1)
        assert (len(kept), total, excess) == (1, 100, 100)


class TestVerifyEnforcedCatchesAFilteredIndex(TransactionTestCase):
    """The one thing introspection cannot see.

    `get_constraints()` returns the same dict for a full unique index and a filtered
    one - measured - so a filtered index reads as enforcing while still permitting
    duplicates among the rows it excludes. Predicates are not reachable through the
    ORM, so the command checks the symptom instead.

    **The column set used here is `Room.name` alone, which the database does not
    enforce** - the real constraint is on `(site, name)`. That is deliberate: it lets
    two rows legitimately share a name, which is the state a filtered index would allow
    while still reporting itself as unique. Trying to stage this on the genuinely
    enforced `(site, name)` just raises `IntegrityError` on SQLite, because SQLite is
    not the backend this repair exists for.
    """

    def two_rooms_sharing_a_name(self, name):
        from qatrack.parts.models import Room
        from qatrack.units.models import Site

        for n in (1, 2):
            site = Site.objects.create(name="%s-site-%d" % (name, n),
                                       slug="%s-site-%d" % (name, n))
            Room.objects.create(name=name, site=site)
        return frozenset([Room._meta.get_field("name").column])

    def claiming_enforced(self, columns):
        """Claim this column set is declared and enforced - **for `Room` only**.

        Scoping matters. A blanket mock claims every model declares a set containing a
        `name` column, and plenty of other tables legitimately have repeated names, so
        the command then reports those and the clean case cannot be distinguished from
        the dirty one. The first version of this helper did exactly that.
        """
        from qatrack.parts.models import Room

        where = ("qatrack.qatrack_core.management.commands"
                 ".check_unique_constraints.%s")

        def only_room(model, *args, **kwargs):
            return {columns} if model is Room else set()

        def enforced(connection, table, *args, **kwargs):
            return {columns} if table == Room._meta.db_table else set()

        return (
            mock.patch(where % "enforced_unique_columns", side_effect=enforced),
            mock.patch(where % "declared_unique_columns", side_effect=only_room),
        )

    def test_duplicates_behind_an_enforced_set_are_reported(self):
        columns = self.two_rooms_sharing_a_name("dup")
        enforced, declared = self.claiming_enforced(columns)
        with enforced, declared:
            output = run(verify_enforced=True)

        assert "reported as enforced" in output, output
        assert "probably filtered" in output
        assert "reported as enforced but contain duplicates" in output

    def test_without_the_flag_it_stays_quiet(self):
        """The scan is opt-in: it costs a table scan per enforced set."""
        columns = self.two_rooms_sharing_a_name("quiet")
        enforced, declared = self.claiming_enforced(columns)
        with enforced, declared:
            output = run()

        assert "reported as enforced" not in output
        assert "Nothing to repair" in output

    def test_a_clean_enforced_set_is_not_reported(self):
        """Without this, the test above would pass if the flag reported everything."""
        from qatrack.parts.models import Room
        from qatrack.units.models import Site

        site = Site.objects.create(name="solo-site", slug="solo-site")
        Room.objects.create(name="solo", site=site)
        columns = frozenset([Room._meta.get_field("name").column])

        enforced, declared = self.claiming_enforced(columns)
        with enforced, declared:
            output = run(verify_enforced=True)

        assert "reported as enforced" not in output, output

class TestItPrintsTheRepairStatement(TransactionTestCase):
    """The blocked-repair message sends administrators here for the statement.

    `TransactionTestCase`, not `TestCase`: asking Django to render the statement
    needs a schema editor, and SQLite refuses to open one inside an enclosing
    `atomic()` block. The command itself does not run in a transaction, so this
    is a constraint of the test harness rather than of the command.

    Before this, the command printed no SQL at all, so following that
    instruction gave them nothing. Django renders the statement, so these tests
    check that one is produced and that it is the right shape rather than
    asserting an exact string per backend.
    """

    def render(self, model, field_names):
        out = StringIO()
        command = Command(stdout=out)
        command.write_repair_sql(connection, model, field_names)
        return out.getvalue()

    def test_a_statement_is_printed_for_a_declared_unique_set(self):
        """Each backend writes this its own way, so check the shape, not the words.

        Django renders `CREATE UNIQUE INDEX ...` on SQLite and
        `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE (...)` on PostgreSQL. Asserting
        either by name passes on one engine and fails on the others, which is how
        this test first failed in CI.
        """
        from qatrack.units.models import Unit
        output = self.render(Unit, ['number'])
        assert 'repair with:' in output, output
        assert Unit._meta.db_table in output, output
        assert 'UNIQUE' in output.upper(), output
        assert ('CREATE UNIQUE INDEX' in output.upper()
                or 'ADD CONSTRAINT' in output.upper()), output

    def test_a_nullable_column_gets_the_partial_form_where_the_backend_has_one(self):
        """And says so plainly where it has none, which MySQL does not.

        This test asserted only that `repair with:` appeared, and on MySQL it did -
        above the word `None`, because Django returns no statement for a partial index
        MySQL cannot create and the command stringified it anyway. So the engine where
        the statement does not exist was the engine the test said least about.
        """
        from qatrack.service_log.models import Hours
        output = self.render(Hours, ['service_event', 'third_party', 'user'])
        assert 'None' not in output, output
        if connection.features.supports_partial_indexes:
            assert 'repair with:' in output, output
            assert 'WHERE' in output.upper(), output
        else:
            assert 'repair with:' not in output, output
            assert 'no statement for it' in output, output

    def test_an_unmappable_set_is_reported_rather_than_crashing(self):
        from qatrack.units.models import Unit
        output = self.render(Unit, ['not_a_field'])
        assert 'could not render' in output, output
        assert 'Traceback' not in output
