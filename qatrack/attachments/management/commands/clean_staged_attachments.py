"""Remove staged attachments that no session could still be using.

A file attached while performing QC is written to ``MEDIA_ROOT/uploads/tmp``
and its ``Attachment`` row is created at once; both are moved into place only
when the test list instance is saved. Abandon the form and the pair stays
there, and nothing else in QATrack+ removes it, so the folder grows with every
abandoned upload.

**Everything else under the media folder is records and must never be deleted.**
This command exists because staging files are the one exception: a file here
was never attached to anything. It still refuses to be casual about it - see
the boundary below, and note that it reports by default and only deletes when
asked.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from qatrack.attachments.models import Attachment

# Days beyond AUTOSAVE_DAYS_TO_KEEP before a staged file may be swept.
#
# The boundary is the autosave window plus a margin, not the window itself.
# An in-progress session a user can still resume refers to its staged uploads
# by id, and that resumability lasts AUTOSAVE_DAYS_TO_KEEP days - so anything
# inside that window may still be wanted. The margin covers the cases where
# the two clocks do not line up: `clean_autosaves` runs on its own schedule
# rather than at the instant a row expires, a server's time may have been
# adjusted, and an attachment's `created` is not the same moment as the
# autosave that refers to it. Nothing is lost by waiting a few more days, and
# a record could be lost by not.
DEFAULT_MARGIN_DAYS = 7


class Command(BaseCommand):
    help = (
        "Report, and with --delete remove, staged (unfinalized) attachments older "
        "than AUTOSAVE_DAYS_TO_KEEP plus a margin."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--margin-days",
            type=int,
            default=DEFAULT_MARGIN_DAYS,
            help=(
                "Days beyond AUTOSAVE_DAYS_TO_KEEP before a staged file may be "
                "removed (default %d)." % DEFAULT_MARGIN_DAYS
            ),
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Actually remove them. Without this the command only reports.",
        )

    def handle(self, *args, **options):
        margin = options["margin_days"]
        if margin < 0:
            raise CommandError("--margin-days cannot be negative.")

        keep_days = getattr(settings, "AUTOSAVE_DAYS_TO_KEEP", 30)
        boundary_days = keep_days + margin
        cutoff = timezone.now() - timezone.timedelta(days=boundary_days)

        self.stdout.write(
            "Sweep boundary: AUTOSAVE_DAYS_TO_KEEP (%d) + %d = %d days, so anything "
            "staged before %s." % (
                keep_days, margin, boundary_days, cutoff.isoformat(timespec="seconds"),
            )
        )

        # `finalized` is a per-row property, not a column, so the filtering is
        # done here. `created` is indexed-ish enough for this to stay cheap at
        # the scale a staging folder reaches, and the date filter is applied in
        # the query so only candidates are considered.
        candidates = [
            attachment
            for attachment in Attachment.objects.filter(created__lt=cutoff).iterator()
            if not attachment.finalized
        ]

        if not candidates:
            self.stdout.write(self.style.SUCCESS("Nothing to sweep."))
            return

        total_bytes = 0
        for attachment in candidates:
            try:
                total_bytes += attachment.attachment.size
            except Exception:  # noqa: BLE001 - the file may already be gone
                pass

        self.stdout.write(
            "%d staged attachment(s) past the boundary, %.1f MiB."
            % (len(candidates), total_bytes / (1024 * 1024))
        )

        if not options["delete"]:
            self.stdout.write(self.style.WARNING(
                "Reporting only. Pass --delete to remove them."
            ))
            return

        removed_rows = 0
        removed_files = 0
        for attachment in candidates:
            path = None
            try:
                path = attachment.attachment.path
            except Exception:  # noqa: BLE001 - storage without a local path
                path = None

            # The row goes first, inside a transaction, and the file after it.
            # The other order can leave a row pointing at a file that is gone,
            # which is precisely what `check_attachments` exists to report - a
            # cleanup must not manufacture the fault another command audits.
            with transaction.atomic():
                attachment.delete()
            removed_rows += 1

            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    removed_files += 1
                except OSError as e:
                    # Said out loud rather than swallowed: a file left behind is
                    # harmless, but an operator who asked for a sweep should know
                    # it did not finish.
                    self.stderr.write(self.style.ERROR(
                        "Could not remove %s: %s" % (path, e)
                    ))

        self.stdout.write(self.style.SUCCESS(
            "Removed %d staged attachment row(s) and %d file(s)."
            % (removed_rows, removed_files)
        ))
