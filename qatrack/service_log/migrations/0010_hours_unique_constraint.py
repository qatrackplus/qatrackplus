"""Intentionally empty. This migration never created anything.

It was written in 2018 to add four partial unique indexes to `service_log_hours`,
covering the NULL combinations that a plain `unique_together` does not constrain -
`(service_event, third_party, user)` has two nullable columns, and standard SQL treats
NULLs as distinct, so duplicates are permitted wherever either is NULL.

**It has never run.** The body was:

    def forward(apps, schema_editor):
        if schema_editor.connection.vendor == 'mysql':
            return
        migrations.RunSQL(CREATE_PARTIAL_INDEX)

`RunSQL` is an operation *class*. Constructing one inside a `RunPython` function and
discarding the result executes nothing; it needed `schema_editor.execute(...)`. Verified
on every database checked: no `hours_*_uni_idx` index exists anywhere.

The body is removed rather than corrected, for two reasons.

**It is recorded as applied on every installation**, so correcting it would change
nothing for any existing database and would make fresh installs diverge from upgraded
ones. A fix belongs in a new migration.

**And the invariant is not actually missing.** `qatrack.service_log.models`'s
`ensure_hours_unique` `pre_save` receiver performs the same check in Python - its own
docstring says "Some DB's don't consider multiple rows which contain the same columns and
include null to violate unique constraints so we do our own check" - so every ORM write
on every engine has been enforcing this all along. Whether that rule is the right one is
a separate question, deferred to 4.1.

What is left is the file, keeping its name and dependency so the migration graph is
unchanged. The operations list is empty because that is what this migration has always
effectively been.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('service_log', '0009_auto_20180411_1644'),
    ]

    operations = []
