"""The cache table has to exist after `migrate`, with nothing else run.

Until `qatrack_core.0002_cache_table`, `CACHES` pointed at a table that only
`manage.py createcachetable` created, so a migrated database could still raise
`no such table: qatrack_cache_table` on an ordinary save - every cached count is
invalidated from a `post_save` receiver, and those run on every write.
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import TestCase


class TestCacheTableExists(TestCase):
    """The test database is built by running the migrations, so this asserts the
    migration did it - nothing in the test suite calls `createcachetable`."""

    def test_the_cache_table_was_created_by_a_migration(self):
        location = settings.CACHES["default"].get("LOCATION")
        if not settings.CACHES["default"]["BACKEND"].endswith("db.DatabaseCache"):
            self.skipTest("this installation is not using a database cache")
        assert location in connection.introspection.table_names(), (
            "%s is missing: `migrate` alone has to leave a usable cache" % location
        )

    def test_the_cache_round_trips(self):
        cache.set("qatrack-cache-probe", 1)
        assert cache.get("qatrack-cache-probe") == 1

    def test_an_ordinary_save_does_not_need_createcachetable(self):
        """Creating a user invalidates six cached counts through
        `qa.signals.update_unreviewed_cache`. Before the migration this raised."""
        User.objects.create_user("cache-table-probe", "a@b.com", "password")
        assert User.objects.filter(username="cache-table-probe").exists()


class TestRawSavesSkipTheCache(TestCase):
    """`loaddata` saves with `raw=True` and the receivers still fire. They now
    return early: a fixture load should not be invalidating per-request badges,
    and on a database whose cache table is absent it aborted the load outright."""

    def test_receivers_return_early_for_raw_saves(self):
        from qatrack.faults.signals import update_faults_cache
        from qatrack.qa.signals import update_unreviewed_cache
        from qatrack.service_log.signals import update_colours, update_se_cache

        cache.set(settings.CACHE_UNREVIEWED_COUNT, "kept")
        cache.set(settings.CACHE_UNREVIEWED_FAULT_COUNT, "kept")
        cache.set(settings.CACHE_SE_NEEDING_REVIEW_COUNT, "kept")

        update_unreviewed_cache(sender=User, raw=True)
        update_faults_cache(sender=User, raw=True)
        update_se_cache(sender=User, raw=True)
        update_colours(sender=User, raw=True)

        assert cache.get(settings.CACHE_UNREVIEWED_COUNT) == "kept"
        assert cache.get(settings.CACHE_UNREVIEWED_FAULT_COUNT) == "kept"
        assert cache.get(settings.CACHE_SE_NEEDING_REVIEW_COUNT) == "kept"

    def test_a_real_save_still_invalidates(self):
        """The guard is specific to raw, not a blanket early return."""
        cache.set(settings.CACHE_UNREVIEWED_COUNT, "stale")
        update = __import__("qatrack.qa.signals", fromlist=["update_unreviewed_cache"])
        update.update_unreviewed_cache(sender=User)
        assert cache.get(settings.CACHE_UNREVIEWED_COUNT) is None
