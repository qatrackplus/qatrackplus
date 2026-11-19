"""Upgrading from 3.1.x must not stop on saved reports whose filters aren't JSON.

`reports.0009` turns `SavedReport.filters` from a text column into a JSONField,
which adds a JSON check on every engine. The 3.1.x admin saved the filters
textarea back in Python format (`{'active': True}`), and `dumpdata` wrote the
field the same way, so a site that had ever edited a saved report in the admin,
or had moved its database with `dumpdata`/`loaddata`, failed `migrate` with an
IntegrityError on SQL Server. 0009 now repairs those rows first.

MySQL can't roll back schema changes, so a site whose 0009 had already failed
there was left with the two columns 0009 adds first, and the rerun stopped on
"Duplicate column name". 0009 now removes those before adding them again.
"""

import json
from importlib import import_module
from unittest import mock

from django.contrib.auth.models import User
from django.db import connection, migrations
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TransactionTestCase

from qatrack.reports.models import SavedReport

BEFORE = [('reports', '0008_auto_20200722_1707')]

migration = import_module('qatrack.reports.migrations.0009_Auto_BigAuto_TimeZone_Django42')


class TestFiltersAsDict(SimpleTestCase):
    def test_json_is_read_as_json(self):
        assert migration._filters_as_dict('{"unit": [1, 2], "active": true}') == {'unit': [1, 2], 'active': True}

    def test_a_python_repr_from_the_admin_is_read_back_exactly(self):
        raw = str({'unit': [1, 2], 'active': True, 'site': None, 'title': "it's"})
        assert migration._filters_as_dict(raw) == {'unit': [1, 2], 'active': True, 'site': None, 'title': "it's"}

    def test_double_encoded_json_is_unwrapped(self):
        assert migration._filters_as_dict(json.dumps(json.dumps({'a': 1}))) == {'a': 1}

    def test_empty_filters_become_an_empty_dict(self):
        assert migration._filters_as_dict('') == {}
        assert migration._filters_as_dict(None) == {}

    def test_unreadable_filters_are_reported_as_none(self):
        assert migration._filters_as_dict('not filters at all') is None
        assert migration._filters_as_dict('[1, 2]') is None

    def test_python_values_with_no_json_form_are_reported_as_none(self):
        # literal_eval reads these, but json.dumps can't write them, so they must not reach the UPDATE
        assert migration._filters_as_dict("{'unit': {1, 2}}") is None
        assert migration._filters_as_dict("{'unit': b'1'}") is None
        assert migration._filters_as_dict("{(1, 2): 'unit'}") is None

    def test_nan_is_not_treated_as_json(self):
        # json.loads accepts NaN, but the JSON check this migration adds does not
        assert migration._filters_as_dict('{"value": NaN}') is None
        assert migration._filters_as_dict('{"value": Infinity}') is None


class TestMigratingFrom31SavedReports(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor

    def setUp(self):
        self.addCleanup(self.migrate_to_latest)
        executor = self.migrate(BEFORE)
        self.old_apps = executor.loader.project_state(BEFORE).apps

    def migrate_to_latest(self):
        executor = MigrationExecutor(connection)
        self.migrate(executor.loader.graph.leaf_nodes())

    def save_old_report(self, title, filters):
        user = User.objects.get_or_create(username='reporter')[0]
        OldSavedReport = self.old_apps.get_model('reports', 'SavedReport')
        return OldSavedReport.objects.create(
            title=title,
            report_type='testlistinstance_summary',
            report_format='pdf',
            filters=filters,
            created_by_id=user.pk,
            modified_by_id=user.pk,
        ).pk

    def test_reports_saved_from_the_31_admin_survive_the_upgrade(self):
        from_page = self.save_old_report('from page', json.dumps({'unit': [1], 'active': True}))
        from_admin = self.save_old_report('from admin', str({'unit': [1], 'active': True}))
        from_dumpdata = self.save_old_report('from dumpdata', str({'unit': [2], 'site': None}))
        unreadable = self.save_old_report('unreadable', 'not filters at all')
        with_a_set = self.save_old_report('with a set', str({'unit': {1, 2}}))
        with_nan = self.save_old_report('with NaN', '{"value": NaN}')

        self.migrate_to_latest()

        assert SavedReport.objects.get(pk=from_page).filters == {'unit': [1], 'active': True}
        assert SavedReport.objects.get(pk=from_admin).filters == {'unit': [1], 'active': True}
        assert SavedReport.objects.get(pk=from_dumpdata).filters == {'unit': [2], 'site': None}
        assert SavedReport.objects.get(pk=unreadable).filters == {}
        assert SavedReport.objects.get(pk=with_a_set).filters == {}
        assert SavedReport.objects.get(pk=with_nan).filters == {}

    def run_0009s_add_fields(self, backwards=False):
        """Run 0009's own AddField steps, as a run that failed after them had (or undo them)."""
        add_fields = [op for op in migration.Migration.operations if isinstance(op, migrations.AddField)]
        assert [op.name for op in add_fields] == ['include_logo', 'paper_size']
        states = [MigrationExecutor(connection).loader.project_state(BEFORE)]
        for op in add_fields:
            states.append(states[-1].clone())
            op.state_forwards('reports', states[-1])
        with connection.schema_editor() as editor:
            steps = list(zip(add_fields, states, states[1:]))
            for op, before, after in reversed(steps) if backwards else steps:
                if backwards:
                    op.database_backwards('reports', editor, after, before)
                else:
                    op.database_forwards('reports', editor, before, after)

    def add_the_columns_a_failed_0009_leaves_on_mysql(self):
        self.run_0009s_add_fields()

    def savedreport_columns(self):
        with connection.cursor() as cursor:
            return {c.name for c in connection.introspection.get_table_description(cursor, 'reports_savedreport')}

    def test_rerunning_0009_after_it_failed_on_mysql_succeeds(self):
        report = self.save_old_report('saved before the failed upgrade', str({'unit': [1]}))
        self.add_the_columns_a_failed_0009_leaves_on_mysql()
        assert {'include_logo', 'paper_size'} <= self.savedreport_columns()

        if connection.features.can_rollback_ddl:
            # Only an engine without transactional DDL (MySQL) can be left in this state, and
            # there the step runs inside the migrate below. Elsewhere, run it as MySQL would.
            with mock.patch.object(connection.features, 'can_rollback_ddl', False):
                with connection.schema_editor() as editor:
                    migration.drop_columns_left_by_a_failed_0009(self.old_apps, editor)
            assert not {'include_logo', 'paper_size'} & self.savedreport_columns()

        self.migrate_to_latest()

        report = SavedReport.objects.get(pk=report)
        assert report.include_logo is True
        assert report.paper_size == 'letter'
        assert report.filters == {'unit': [1]}

    def test_the_column_step_leaves_engines_that_roll_back_ddl_alone(self):
        if not connection.features.can_rollback_ddl:
            self.skipTest('this engine cannot roll back DDL, so the step is meant to act here')
        self.add_the_columns_a_failed_0009_leaves_on_mysql()
        with connection.schema_editor() as editor:
            migration.drop_columns_left_by_a_failed_0009(self.old_apps, editor)
        assert {'include_logo', 'paper_size'} <= self.savedreport_columns()
        # put the table back the way 0008 left it, so the cleanup migration can add them
        self.run_0009s_add_fields(backwards=True)
