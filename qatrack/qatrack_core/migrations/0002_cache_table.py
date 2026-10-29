"""Create the cache table that `CACHES` points at, if the database is the backend.

Until this migration, `qatrack_cache_table` was created only by
`manage.py createcachetable`, which means it was schema that lived outside the
migration graph: `migrate` could finish successfully and leave an installation
that cannot save a row. Every write path that invalidates a cached count - a
completed test list, a reviewed service event, a new user - issues a DELETE
against this table from a `post_save` receiver, so without it

    User.objects.create_user(...)

raises `OperationalError: no such table: qatrack_cache_table`. Measured on
SQLite, PostgreSQL 16 and MySQL 8. Nothing reported it either: `manage.py check`
passes on a database with no cache table, and the installation guide ran
`createcachetable` forty lines after the `loaddata` that needs it (#844), while
the Docker entrypoint ran it first.

Creating it here removes the ordering question rather than answering it.

This delegates to Django's own `createcachetable`, which is idempotent - it
reports "Cache table 'x' already exists." and returns - so the migration is a
no-op on every installation that followed the documentation. It runs only for
cache backends that are actually database tables; a site using local memory,
Redis or memcached gets nothing, and reversing it drops nothing, because a
cache table holds no data a site would miss.
"""

from django.core.management import call_command
from django.db import migrations


def cache_table_names(settings):
    """The table of every configured database cache, in definition order.

    Decided by the backend's **type**, not by its dotted path. A suffix check on
    `BACKEND` - `endswith("db.DatabaseCache")` - misses a subclass living under
    another module path, and `migrate` would then finish while leaving that
    cache's table uncreated and the cache unusable, which is the exact failure
    this migration exists to remove. Django's own `createcachetable` discovers
    them this way, with `isinstance(cache, BaseDatabaseCache)`.

    `cache._table` rather than `LOCATION`, for the same reason: it is the table
    name the backend resolved, whatever the config said.

    A backend that cannot even be constructed is skipped rather than raising. A
    migration is the wrong place to fail on an unrelated misconfigured cache,
    and `qatrack.W015` reports a missing cache table afterwards.
    """
    from django.core.cache import caches
    from django.core.cache.backends.db import BaseDatabaseCache

    names = []
    for alias in getattr(settings, "CACHES", {}):
        try:
            cache = caches[alias]
        except Exception:  # noqa: BLE001 - see docstring
            continue
        if isinstance(cache, BaseDatabaseCache):
            table = getattr(cache, "_table", None)
            if table and table not in names:
                names.append(table)
    return names


def create_cache_tables(apps, schema_editor):
    from django.conf import settings

    names = cache_table_names(settings)
    if not names:
        return
    # `createcachetable` consults the router itself
    # (`router.allow_migrate_model`), so on a multi-database site it may
    # legitimately decline: a router that places the cache table on a dedicated
    # cache database, while denying `qatrack_core` migrations there, leaves this
    # RunPython running only where the table is not wanted and declining where
    # it is. A migration cannot reach across that - it runs where its own app is
    # migrated and nowhere else.
    #
    # So this does the common case and does not pretend to do the other.
    # `qatrack.W015` checks that each configured cache table actually exists and
    # reports the ones that do not, which covers the routed case, a subclassed
    # backend this missed, and a site that simply never ran anything.
    call_command(
        "createcachetable",
        *names,
        database=schema_editor.connection.alias,
        verbosity=0,
    )


def drop_cache_tables(apps, schema_editor):
    """Reverse by doing nothing.

    A cache table holds derived values with a lifetime of minutes. Dropping it
    on reverse would break the installation it was reversed on, for no gain, so
    this is deliberately a no-op rather than a DROP TABLE.
    """


class Migration(migrations.Migration):

    dependencies = [
        ("qatrack_core", "0001_update_recurrences"),
    ]

    operations = [
        migrations.RunPython(create_cache_tables, drop_cache_tables),
    ]
