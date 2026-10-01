"""Find the rows that would block re-creating a missing unique index.

`qatrack.W011` reports *that* the database is not enforcing uniqueness a model
declares. This reports *why it cannot simply be re-added*: the rows already there
that violate it.

Separate from the check, and a command rather than a second check, for the same
reason `check_translations` is: checks run on every `migrate` and on
`manage.py check`, and scanning tables for duplicates is too expensive to do
there. This is run deliberately, before the repair migration.
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.models import Count

from qatrack.qatrack_core.checks import (
    declared_unique_columns,
    enforced_unique_columns,
    unenforced_unique_columns,
)


def fields_for_columns(model, columns):
    """Map database column names back to field names, for ORM queries.

    Returns None if any column cannot be mapped, so the caller can report the
    column set rather than silently scanning the wrong thing.
    """
    by_column = {f.column: f.name for f in model._meta.local_fields}
    try:
        return [by_column[c] for c in columns]
    except KeyError:
        return None


def duplicate_groups(model, field_names):
    """Groups of rows sharing a value for `field_names`, NULLs excluded.

    NULLs are excluded deliberately, because that is what the index this is
    validating will do. Django's `unique=True` on a nullable column permits many
    NULLs - standard SQL treats them as distinct - so the index that matches the
    model's intent is a filtered one, and a row with a NULL is not a duplicate.
    Counting NULL groups here would report rows the repair does not care about.
    """
    qs = model.objects.all()
    for name in field_names:
        qs = qs.exclude(**{"%s__isnull" % name: True})
    return (
        qs.values(*field_names)
        .annotate(num=Count("pk"))
        .filter(num__gt=1)
        .order_by("-num")
    )


class Command(BaseCommand):
    help = "Report rows that would block re-creating a unique index the database has lost"

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="default",
            help="Database alias to inspect (default: default).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Most duplicate groups to list per model (default: 20). Counts are always complete.",
        )

    def handle(self, *args, **options):
        connection = connections[options["database"]]
        limit = options["limit"]

        self.stdout.write("Database: %s (%s)" % (options["database"], connection.vendor))

        checked = 0
        unenforced_total = 0
        blocked = []

        for model in apps.get_models():
            if not model._meta.managed:
                continue
            declared = declared_unique_columns(model)
            if not declared:
                continue
            checked += 1
            try:
                enforced = enforced_unique_columns(connection, model._meta.db_table)
            except Exception as e:  # noqa: BLE001 - a missing table is not this command's problem
                self.stdout.write(
                    self.style.WARNING("  %s: could not introspect %s (%s)" % (
                        model._meta.label, model._meta.db_table, e))
                )
                continue

            for columns in unenforced_unique_columns(declared, enforced):
                unenforced_total += 1
                field_names = fields_for_columns(model, columns)
                if field_names is None:
                    self.stdout.write(self.style.WARNING(
                        "  %s %s: cannot map these columns to fields; check by hand"
                        % (model._meta.label, columns)
                    ))
                    continue

                groups = list(duplicate_groups(model, field_names))
                if not groups:
                    self.stdout.write(self.style.SUCCESS(
                        "  OK   %s %s - not enforced, no duplicates" % (model._meta.label, columns)
                    ))
                    continue

                excess = sum(g["num"] - 1 for g in groups)
                blocked.append((model._meta.label, columns, len(groups), excess))
                self.stdout.write(self.style.ERROR(
                    "  DUPS %s %s - %d duplicated value%s, %d row%s to resolve"
                    % (model._meta.label, columns, len(groups),
                       "" if len(groups) == 1 else "s", excess, "" if excess == 1 else "s")
                ))
                for g in groups[:limit]:
                    values = ", ".join("%s=%r" % (n, g[n]) for n in field_names)
                    self.stdout.write("         %s (%d rows)" % (values, g["num"]))
                if len(groups) > limit:
                    self.stdout.write("         ... and %d more" % (len(groups) - limit))

        self.stdout.write("")
        self.stdout.write("%d models declare uniqueness; %d column set%s not enforced by this database."
                          % (checked, unenforced_total, "" if unenforced_total == 1 else "s"))

        if not unenforced_total:
            self.stdout.write(self.style.SUCCESS(
                "Nothing to repair - every declared unique constraint is enforced here."
            ))
            return

        if blocked:
            self.stdout.write(self.style.ERROR(
                "%d of them cannot be re-added until the rows above are resolved." % len(blocked)
            ))
            self.stdout.write(
                "Resolve each by deciding which row is correct and changing or deleting the others, "
                "then run this again. The repair migration skips an index it cannot create and says so, "
                "so it will not fail the upgrade - but the constraint stays unenforced until this is clear."
            )
        else:
            self.stdout.write(self.style.SUCCESS(
                "No duplicates - the repair migration can re-create every one of them."
            ))
