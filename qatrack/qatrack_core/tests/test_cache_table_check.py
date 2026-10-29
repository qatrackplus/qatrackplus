"""`qatrack.W015`: a configured database cache must have its table.

`qatrack_core.0002_cache_table` creates them during `migrate`, and cannot cover three
cases - a cache table a router puts on another database, a backend subclass the
migration did not recognise, and a site that migrated before any of this existed. The
check covers what the migration structurally cannot.

Why it matters at all: every write that invalidates a cached count DELETEs from that
table in a `post_save` receiver, so creating a user raises `no such table`. Until this
check, `manage.py check` passed on such a database, which is what turned it into a
surprise mid-upgrade.
"""

from unittest import mock

from django.core.cache.backends.db import DatabaseCache
from django.core.management import call_command
from django.test import TestCase, override_settings

from qatrack.qatrack_core.checks import check_cache_tables_exist, configured_cache_tables

DB_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'qatrack_cache_table',
    }
}


class MyDatabaseCache(DatabaseCache):
    """A subclass under a different module path - still a database cache.

    This is the shape the migration's old `BACKEND.endswith("db.DatabaseCache")`
    check missed, which @coderabbitai raised as Major on c#13.
    """


SUBCLASS_CACHE = {
    'default': {
        'BACKEND': 'qatrack.qatrack_core.tests.test_cache_table_check.MyDatabaseCache',
        'LOCATION': 'qatrack_cache_table',
    }
}

NON_DB_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}


class TestDetectionIsByType(TestCase):

    @override_settings(CACHES=DB_CACHE)
    def test_the_plain_database_cache_is_found(self):
        assert configured_cache_tables() == [('default', 'qatrack_cache_table')]

    @override_settings(CACHES=SUBCLASS_CACHE)
    def test_a_subclass_under_another_module_path_is_found(self):
        """The finding: a dotted-path suffix test would miss this."""
        assert configured_cache_tables() == [('default', 'qatrack_cache_table')]

    @override_settings(CACHES=NON_DB_CACHE)
    def test_a_non_database_cache_is_not_reported(self):
        assert configured_cache_tables() == []

    @override_settings(CACHES=SUBCLASS_CACHE)
    def test_the_migration_helper_agrees(self):
        """The migration and the check must not disagree about what a db cache is."""
        from importlib import import_module

        from django.conf import settings

        migration = import_module('qatrack.qatrack_core.migrations.0002_cache_table')
        assert migration.cache_table_names(settings) == ['qatrack_cache_table']


class TestTheCheckFires(TestCase):

    @override_settings(CACHES=DB_CACHE)
    def test_nothing_is_reported_when_the_table_exists(self):
        """With the table present, the check is silent.

        The table is created here rather than relied on: `test_settings.py`
        configures a local-memory cache, so the migration that would create the
        table finds no database cache to create one for. Creating it under the
        override keeps this test about the check rather than about which cache
        backend the test settings happen to name.
        """
        call_command('createcachetable')
        assert check_cache_tables_exist(databases=['default']) == []

    @override_settings(CACHES=DB_CACHE)
    def test_a_missing_table_is_reported(self):
        with mock.patch('django.db.backends.base.introspection.BaseDatabaseIntrospection'
                        '.table_names', return_value=[]):
            problems = check_cache_tables_exist(databases=['default'])
        assert len(problems) == 1, problems
        assert problems[0].id == 'qatrack.W015'
        assert 'qatrack_cache_table' in problems[0].msg
        assert 'createcachetable' in problems[0].hint

    @override_settings(CACHES=NON_DB_CACHE)
    def test_a_non_database_cache_is_never_reported(self):
        with mock.patch('django.db.backends.base.introspection.BaseDatabaseIntrospection'
                        '.table_names', return_value=[]):
            assert check_cache_tables_exist(databases=['default']) == []

    @override_settings(CACHES=DB_CACHE)
    def test_no_databases_means_no_work(self):
        """Django only passes `databases` for database-tagged runs."""
        assert check_cache_tables_exist(databases=None) == []

    @override_settings(CACHES=DB_CACHE)
    def test_a_router_that_puts_the_table_elsewhere_silences_it(self):
        """A routed cache table is not missing from this database; it belongs elsewhere.

        Without this the check would nag every multi-database site that does exactly
        what Django documents.
        """
        with mock.patch('django.db.backends.base.introspection.BaseDatabaseIntrospection'
                        '.table_names', return_value=[]), \
             mock.patch('django.db.router.allow_migrate_model', return_value=False):
            assert check_cache_tables_exist(databases=['default']) == []
