"""Give fault types with an unusable slug a working one.

`FaultType.save()` has always built the slug from the code, and a code with no
ASCII form - a Chinese code, say - slugified to an empty string. The field
allows it, the URL patterns do not: `{% url %}` then raises `NoReverseMatch`
and every page listing that fault type returns a 500.

The generator was fixed to fall back to the model name, but only on save, so
records written before that fix keep their broken slug until somebody edits
them - which, given their pages 500, is not something anyone can do through
the site. Raised by Copilot on PR crcrewso#18.

A command rather than a data migration, deliberately. Both 4.0.x upgrade
guides promise "no database migrations", and a migration that silently
rewrites identifiers which appear in URLs is the kind of thing an
administrator should get to look at first. `--dry-run` shows what would
change.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from qatrack.faults.models import FaultType
from qatrack.qatrack_core.utils import unique_slug_generator


class Command(BaseCommand):
    help = "Repair fault types whose slug is empty or not a usable URL identifier."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change and write nothing.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Only the unusable ones. A slug that works is left exactly as it is,
        # including its uniqueness counter: rewriting a working slug would
        # change a working URL, which is the one thing this must not do.
        broken = [
            fault_type for fault_type in FaultType.objects.all().order_by("pk")
            if not (fault_type.slug or "").strip()
        ]

        if not broken:
            self.stdout.write("No fault type needs repair.")
            return

        self.stdout.write(
            "%d fault type%s with an unusable slug:"
            % (len(broken), "" if len(broken) == 1 else "s")
        )

        repairs = []
        for fault_type in broken:
            # The generator excludes the instance itself, so a repair cannot
            # collide with the record it is repairing.
            proposed = unique_slug_generator(fault_type, fault_type.code)
            repairs.append((fault_type, proposed))
            self.stdout.write("  %r (pk %s) -> %r" % (fault_type.code, fault_type.pk, proposed))

        if dry_run:
            self.stdout.write(self.style.WARNING("--dry-run: nothing was written."))
            return

        with transaction.atomic():
            for fault_type, proposed in repairs:
                # update(), not save(): save() would recompute the slug, which
                # is the same value, but would also fire the fault-type signals
                # for what is a repair rather than a change to the record.
                FaultType.objects.filter(pk=fault_type.pk).update(slug=proposed)

        self.stdout.write(self.style.SUCCESS("Repaired %d fault type(s)." % len(repairs)))
