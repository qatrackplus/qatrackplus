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
    """The LOCATIONs of every configured DatabaseCache, in definition order."""
    names = []
    for alias, config in getattr(settings, "CACHES", {}).items():
        backend = config.get("BACKEND", "")
        if backend.endswith("db.DatabaseCache"):
            location = config.get("LOCATION")
            if location and location not in names:
                names.append(location)
    return names


def create_cache_tables(apps, schema_editor):
    from django.conf import settings

    names = cache_table_names(settings)
    if not names:
        return
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
