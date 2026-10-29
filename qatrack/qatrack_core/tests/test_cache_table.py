"""The cache table has to exist after `migrate`, with nothing else run.

Until `qatrack_core.0002_cache_table`, `CACHES` pointed at a table that only
`manage.py createcachetable` created, so a migrated database could still raise
`no such table: qatrack_cache_table` on an ordinary save - every cached count is
invalidated from a `post_save` receiver, and those run on every write.
"""

from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings

from qatrack.service_log import models as sl_models


class TestCacheTableExists(TestCase):
    """The table a configured database cache names has to be there.

    **This does not prove the migration created it,** and the first version of
    this docstring said it did. Django's own `create_test_db()` runs
    `createcachetable` after migrating, so the table is in every freshly built
    test database whatever the migration does - which makes the assertion below
    a check that the installation hangs together, not a guard on
    `0002_cache_table`. @copilot pointed that out on c#13; the guard it was
    missing is `TestTheMigrationCreatesTheTableItself` further down.

    It is also a skip rather than a failure wherever the cache is not a database
    one, and `test_settings.py` pins local memory, so on a default run this class
    measures very little. It is kept for the installation that does configure a
    database cache."""

    def test_the_cache_table_is_present_for_a_database_cache(self):
        location = settings.CACHES["default"].get("LOCATION")
        if not settings.CACHES["default"]["BACKEND"].endswith("db.DatabaseCache"):
            self.skipTest("this installation is not using a database cache")
        assert location in connection.introspection.table_names(), (
            "%s is missing: a configured database cache has to have its table" % location
        )

    def test_the_cache_round_trips(self):
        cache.set("qatrack-cache-probe", 1)
        assert cache.get("qatrack-cache-probe") == 1

    def test_an_ordinary_save_does_not_need_createcachetable(self):
        """Creating a user invalidates six cached counts through
        `qa.signals.update_unreviewed_cache`. Before the migration this raised."""
        User.objects.create_user("cache-table-probe", "a@b.com", "password")
        assert User.objects.filter(username="cache-table-probe").exists()


class TestTheMigrationCreatesTheTableItself(TransactionTestCase):
    """The guarantee the installation instructions were allowed to drop.

    `createcachetable` came out of the install guide and the Docker entrypoint
    because `qatrack_core.0002_cache_table` does it during `migrate`. Nothing was
    testing that: the suite's test database already has the table, created by
    Django's `create_test_db()` after it migrates, so gutting the migration broke
    no test. This one works on a table nothing else touches, so the migration is
    the only thing that can make it appear.

    `TransactionTestCase`, because `createcachetable` opens a schema editor and
    SQLite refuses one inside the atomic block a `TestCase` wraps every test in.
    """

    TABLE = 'qatrack_cache_table_probe'

    def drop_the_probe_table(self):
        with connection.cursor() as cursor:
            cursor.execute('DROP TABLE IF EXISTS %s' % self.TABLE)

    def test_migrating_creates_a_configured_cache_table(self):
        migration = import_module('qatrack.qatrack_core.migrations.0002_cache_table')

        self.addCleanup(self.drop_the_probe_table)
        self.drop_the_probe_table()

        probe_cache = {
            'default': {
                'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
                'LOCATION': self.TABLE,
            }
        }
        with override_settings(CACHES=probe_cache):
            assert self.TABLE not in connection.introspection.table_names(), (
                "the probe table existed before the migration ran"
            )

            with connection.schema_editor() as editor:
                migration.create_cache_tables(apps, editor)

            assert self.TABLE in connection.introspection.table_names(), (
                "`migrate` did not create the table the cache is configured with"
            )

    def test_it_creates_nothing_when_the_cache_is_not_a_database(self):
        """The migration is a no-op for locmem, Redis or memcached, as it claims."""
        migration = import_module('qatrack.qatrack_core.migrations.0002_cache_table')

        self.addCleanup(self.drop_the_probe_table)
        self.drop_the_probe_table()

        with override_settings(CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': self.TABLE,
            }
        }):
            with connection.schema_editor() as editor:
                migration.create_cache_tables(apps, editor)

            assert self.TABLE not in connection.introspection.table_names(), (
                "a local-memory cache got a database table"
            )


class TestRawSavesSkipTheCache(TestCase):
    """`loaddata` saves with `raw=True` and the receivers still fire. They now
    return early: a fixture load should not be invalidating per-request badges,
    and on a database whose cache table is absent it aborted the load outright."""

    def sentinel(self, *keys):
        """Put a recognisable non-count in real cache keys, and take it out again.

        These are the keys the application reads, and the value is a **string** where
        the application expects a count. `get_sl_notification_total` sums three of
        them from a context processor, so a leaked sentinel raises `int + str` on
        every page for the rest of the run - which is what happened during a
        full-suite run on the demo server on 2026-10-13, three tests failing with a
        traceback that pointed nowhere near their own subject.

        A `TestCase` rolls back the database, and the cache here *is* the database,
        so the write usually disappears on its own. "Usually" is the problem: the
        same test on a locmem or Redis cache leaks, and nothing in the file said the
        cleanup was being relied on. So it is explicit.
        """
        for key in keys:
            cache.set(key, "kept")
            self.addCleanup(cache.delete, key)

    def test_receivers_return_early_for_raw_saves(self):
        """All seven guards, each asserted on its own key.

        This covered four of the seven and asserted three keys. It called
        `update_colours` without ever asserting `CACHE_SERVICE_STATUS_COLOURS`, so
        removing *that* guard would still have passed - and the two active-collection
        receivers and `update_rts_cache` were not called at all.
        @coderabbitai pointed that out on c#13.

        Each receiver below is driven with `raw=True` and checked against a key only it
        touches, so a guard removed from any one of the seven fails here.
        """
        from qatrack.faults.signals import update_faults_cache
        from qatrack.qa import models as qa_models
        from qatrack.qa.signals import (
            update_active_unit_test_collections_for_unit_post_save,
            update_active_unit_test_collections_for_unit_utc,
            update_unreviewed_cache,
        )
        from qatrack.qa.tests import utils as qa_utils
        from qatrack.service_log.signals import (
            update_colours,
            update_rts_cache,
            update_se_cache,
        )

        utc = qa_utils.create_unit_test_collection()
        unit = utc.unit
        per_unit_key = settings.CACHE_ACTIVE_UTCS_FOR_UNIT_.format(unit.id)

        self.sentinel(
            settings.CACHE_UNREVIEWED_COUNT,            # update_unreviewed_cache
            settings.CACHE_UNREVIEWED_FAULT_COUNT,      # update_faults_cache
            settings.CACHE_SE_NEEDING_REVIEW_COUNT,     # update_se_cache
            settings.CACHE_DEFAULT_SE_STATUS,           # update_se_cache, status sender
            settings.CACHE_SERVICE_STATUS_COLOURS,      # update_colours
            settings.CACHE_RTS_QA_COUNT,                # update_rts_cache
            settings.CACHE_RTS_INCOMPLETE_QA_COUNT,     # update_rts_cache
            per_unit_key,                               # the two active-collection ones
        )

        update_unreviewed_cache(sender=User, raw=True)
        update_faults_cache(sender=User, raw=True)
        # the status sender, so the CACHE_DEFAULT_SE_STATUS branch is reached too
        update_se_cache(sender=sl_models.ServiceEventStatus, raw=True)
        update_colours(sender=sl_models.ServiceEventStatus, raw=True)
        update_rts_cache(sender=User, raw=True)
        update_active_unit_test_collections_for_unit_utc(
            sender=qa_models.UnitTestCollection, instance=utc, raw=True)
        update_active_unit_test_collections_for_unit_post_save(
            sender=type(unit), instance=unit, raw=True)

        for key, who in (
            (settings.CACHE_UNREVIEWED_COUNT, "update_unreviewed_cache"),
            (settings.CACHE_UNREVIEWED_FAULT_COUNT, "update_faults_cache"),
            (settings.CACHE_SE_NEEDING_REVIEW_COUNT, "update_se_cache"),
            (settings.CACHE_DEFAULT_SE_STATUS, "update_se_cache (status sender)"),
            (settings.CACHE_SERVICE_STATUS_COLOURS, "update_colours"),
            (settings.CACHE_RTS_QA_COUNT, "update_rts_cache"),
            (settings.CACHE_RTS_INCOMPLETE_QA_COUNT, "update_rts_cache"),
            (per_unit_key, "update_active_unit_test_collections_for_unit_*"),
        ):
            assert cache.get(key) == "kept", "%s did not return early for a raw save" % who

    def test_a_real_save_still_invalidates(self):
        """The guard is specific to raw, not a blanket early return."""
        self.addCleanup(cache.delete, settings.CACHE_UNREVIEWED_COUNT)
        cache.set(settings.CACHE_UNREVIEWED_COUNT, "stale")
        update = __import__("qatrack.qa.signals", fromlist=["update_unreviewed_cache"])
        update.update_unreviewed_cache(sender=User)
        assert cache.get(settings.CACHE_UNREVIEWED_COUNT) is None
