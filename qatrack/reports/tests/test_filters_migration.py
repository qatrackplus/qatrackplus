"""Upgrading from 3.1.x must not stop on saved reports whose filters aren't JSON.

`reports.0009` turns `SavedReport.filters` from a text column into a JSONField,
which adds a JSON check on every engine. The 3.1.x admin saved the filters
textarea back in Python format (`{'active': True}`), and `dumpdata` wrote the
field the same way, so a site that had ever edited a saved report in the admin,
or had moved its database with `dumpdata`/`loaddata`, failed `migrate` with an
IntegrityError on SQL Server. 0009 now repairs those rows first.
"""

import json
from importlib import import_module

from django.contrib.auth.models import User
from django.db import connection
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
