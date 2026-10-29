"""Find the rows that would block re-creating a missing unique index.

`qatrack.W014` reports *that* the database is not enforcing uniqueness a model
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

from qatrack.qatrack_core.checks import (
    declared_unique_columns,
    enforced_unique_columns,
    unenforced_unique_columns,
)
from qatrack.qatrack_core.unique_repair import (
    duplicate_groups,
    fields_for_columns,
    repair_sql,
)


def summarise_groups(groups, limit):
    """Walk the groups once, keeping only `limit` of them.

    `list(groups)` defeats `--limit` for the thing that actually hurts: a badly
    affected production table can have millions of duplicated values, and all of them
    were transferred and held in memory so that twenty could be printed. Counts stay
    complete because they are accumulated as we go.

    Returns (kept, total_groups, excess_rows).
    """
    kept = []
    total = 0
    excess = 0
    for group in groups.iterator():
        total += 1
        excess += group["num"] - 1
        if len(kept) < limit:
            kept.append(group)
    return kept, total, excess


class Command(BaseCommand):
    help = "Report rows that would block re-creating a unique index the database has lost"

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="default",
            help="Database alias to inspect (default: default).",
        )
        parser.add_argument(
            "--verify-enforced",
            action="store_true",
            help=(
                "Also look for duplicates in the column sets this database reports as "
                "already enforced. Slower - it scans those tables too - but it is the "
                "only way to catch a *filtered* unique index, which introspection "
                "cannot distinguish from a full one."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Most duplicate groups to list per model (default: 20). Counts are always complete.",
        )

    def write_repair_sql(self, connection, model, field_names):
        """Print the statement that would re-create this constraint.

        Rendered by `unique_repair.repair_sql`, which is also what `qatrack.W014`
        prints, so the two cannot describe the same constraint differently - they
        did until 4.0.2.
        """
        try:
            text = repair_sql(connection, model, field_names)
        except Exception as e:  # noqa: BLE001 - a missing statement is not a failure
            self.stdout.write(
                "         (could not render the repair statement: %s)" % e
            )
            return
        if text is None:
            self.stdout.write(
                "         (this backend has no statement for it: it does not support "
                "the partial index a nullable column needs)"
            )
            return
        self.stdout.write("         repair with: %s;" % text)

    def handle(self, *args, **options):
        connection = connections[options["database"]]
        limit = options["limit"]

        self.stdout.write("Database: %s (%s)" % (options["database"], connection.vendor))

        checked = 0
        unenforced_total = 0
        blocked = []
        uninspectable = []
        contradictory = []

        for model in apps.get_models():
            # Proxy and unmanaged models are both skipped, matching the system check
            # in checks.py. A proxy shares its concrete model's table and declared
            # fields, so without this every unenforced set on that table was reported
            # a second time under the proxy's name.
            if not model._meta.managed or model._meta.proxy:
                continue
            declared = declared_unique_columns(model)
            if not declared:
                continue
            checked += 1
            try:
                enforced = enforced_unique_columns(connection, model._meta.db_table)
            except Exception as e:  # noqa: BLE001 - a missing table is not this command's problem
                uninspectable.append(model._meta.label)
                self.stdout.write(
                    self.style.WARNING("  %s: could not introspect %s (%s)" % (
                        model._meta.label, model._meta.db_table, e))
                )
                continue

            if options["verify_enforced"]:
                # Django's introspection returns the same thing for a full unique index
                # and a filtered one, so a column set reported as enforced may still
                # permit duplicates among the rows the filter excludes. Predicates are
                # not reachable through the ORM; duplicate rows are the symptom, and a
                # symptom is checkable.
                for columns in sorted(declared & enforced, key=sorted):
                    field_names = fields_for_columns(model, columns)
                    if field_names is None:
                        continue
                    _, total_groups, excess = summarise_groups(
                        duplicate_groups(model, field_names, using=options["database"]),
                        limit,
                    )
                    if total_groups:
                        contradictory.append(
                            (model._meta.label, columns, total_groups, excess))
                        self.stdout.write(self.style.ERROR(
                            "  BAD  %s %s - reported as enforced, yet %d duplicated "
                            "value%s present. The index is probably filtered."
                            % (model._meta.label, columns, total_groups,
                               "" if total_groups == 1 else "s")
                        ))

            for columns in unenforced_unique_columns(declared, enforced):
                unenforced_total += 1
                field_names = fields_for_columns(model, columns)
                if field_names is None:
                    self.stdout.write(self.style.WARNING(
                        "  %s %s: cannot map these columns to fields; check by hand"
                        % (model._meta.label, columns)
                    ))
                    continue

                shown, total_groups, excess = summarise_groups(
                    duplicate_groups(model, field_names, using=options["database"]), limit
                )
                if not total_groups:
                    self.stdout.write(self.style.SUCCESS(
                        "  OK   %s %s - not enforced, no duplicates" % (model._meta.label, columns)
                    ))
                    self.write_repair_sql(connection, model, field_names)
                    continue

                blocked.append((model._meta.label, columns, total_groups, excess))
                self.stdout.write(self.style.ERROR(
                    "  DUPS %s %s - %d duplicated value%s, %d row%s to resolve"
                    % (model._meta.label, columns, total_groups,
                       "" if total_groups == 1 else "s", excess, "" if excess == 1 else "s")
                ))
                for g in shown:
                    values = ", ".join("%s=%r" % (n, g[n]) for n in field_names)
                    self.stdout.write("         %s (%d rows)" % (values, g["num"]))
                if total_groups > len(shown):
                    self.stdout.write("         ... and %d more" % (total_groups - len(shown)))
                self.write_repair_sql(connection, model, field_names)

        self.stdout.write("")
        self.stdout.write("%d models declare uniqueness; %d column set%s not enforced by this database."
                          % (checked, unenforced_total, "" if unenforced_total == 1 else "s"))

        if contradictory:
            self.stdout.write(self.style.ERROR(
                "%d column set%s reported as enforced but contain duplicates. An index "
                "covering those columns exists, so the repair migration will skip them, "
                "and it is almost certainly filtered - check its definition in the "
                "database and re-create it unfiltered once the rows are resolved."
                % (len(contradictory), "" if len(contradictory) == 1 else "s")
            ))

        if uninspectable:
            # Saying "everything is enforced" after failing to look at some of it is
            # the one answer this command must never give: it is indistinguishable
            # from a clean result and would send a site into the repair migration
            # believing there is nothing to do.
            self.stdout.write(self.style.WARNING(
                "Inconclusive: %d model%s could not be introspected (%s). Resolve those "
                "before relying on this result - a constraint missing on a table that "
                "could not be read would not appear above."
                % (len(uninspectable), "" if len(uninspectable) == 1 else "s",
                   ", ".join(sorted(uninspectable)))
            ))

        if not unenforced_total:
            if uninspectable:
                self.stdout.write(
                    "Nothing to repair among the models that could be read."
                )
            elif contradictory:
                self.stdout.write(
                    "Nothing missing, but see the contradictions above."
                )
            else:
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
                "No duplicates - nothing in this database blocks the repair."
            ))

        if unenforced_total:
            # This command asks the database what it enforces, so it reports an
            # unenforced set whatever the cause. The 4.0.2 migrations repair the
            # sixteen sets they name, and only those: a set unenforced for some other
            # reason is reported here and `migrate` will not re-create it. The two
            # scopes are deliberately different - say so rather than let the message
            # above be read as a promise about every set listed.
            self.stdout.write(
                "\nWhat the migrations will and will not do: QATrack+ 4.0.2 re-creates the "
                "sixteen column sets the 4.0 SQL Server retype dropped, which its migrations "
                "name individually. A set listed above for any other reason - an index dropped "
                "by hand, or one declared after 4.0.2 - is reported by this command but is not "
                "re-created by `migrate`. Run `manage.py check --database default` after "
                "upgrading: anything still named by qatrack.W014 needs re-creating by hand."
            )
