from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from qatrack.attachments.models import Attachment


class Command(BaseCommand):
    """Audit finalized attachments and report any whose backing file is missing.

    On long-running servers an attachment file on disk can disappear (manual
    cleanup, failed migration, storage move) while its ``Attachment`` row still
    points at it. This command iterates finalized attachments, reports any whose
    backing file no longer exists in storage, and exits non-zero when one or more
    are missing so it can be wired into cron / monitoring.
    """

    help = "Report finalized attachments whose backing file is missing from storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--staging",
            action="store_true",
            help=(
                "Also report staged (unfinalized) attachments, which nothing "
                "removes automatically."
            ),
        )

    def handle(self, *args, **options):
        if options["staging"]:
            self.report_staging()

        missing = []
        storage_errors = 0
        # select_related the owner FKs so the per-row `finalized`/`owner`
        # dereferences below don't issue an extra query for every attachment.
        attachments = Attachment.objects.select_related(*Attachment.OWNER_MODELS)
        for attachment in attachments.iterator():
            if not attachment.finalized:
                # tmp / unfinalized attachments are staging files, not audited.
                continue
            try:
                exists = attachment.file_exists
            except Exception as exc:
                # A storage backend failure on a single attachment must not crash
                # the whole audit. Report it and keep going so the run still exits
                # deterministically for cron / monitoring.
                storage_errors += 1
                self.stderr.write(self.style.ERROR("Failed to check attachment %s: %s" % (attachment.pk, exc)))
                continue
            if not exists:
                missing.append(attachment)

        if not missing and not storage_errors:
            self.stdout.write(self.style.SUCCESS("All finalized attachment files are present."))
            return

        if missing:
            self.stdout.write("pk\towner\tpath")
            for attachment in missing:
                self.stdout.write(
                    "%s\t%s\t%s" % (
                        attachment.pk,
                        attachment.owner or "No Owner",
                        attachment.attachment.name or "<blank>",
                    )
                )

        summary_parts = []
        if missing:
            summary_parts.append("%d finalized attachment(s) are missing their backing file." % len(missing))
        if storage_errors:
            summary_parts.append("%d attachment(s) could not be checked due to storage errors." % storage_errors)
        self.stderr.write(self.style.ERROR(" ".join(summary_parts)))
        # Non-zero exit (missing files and/or storage errors) so the audit can be
        # wired into cron / monitoring.
        raise SystemExit(1)

    def report_staging(self):
        """Report staged attachments, which no scheduled task ever removes.

        A file attached while performing QC is written to MEDIA_ROOT/uploads/tmp
        and its `Attachment` row is created immediately; both are moved into
        place only when the test list instance is saved. Abandon the form -
        navigate away, give up on a validation error, upload a replacement for
        the same test - and the staged row and its file stay where they are.
        Nothing in QATrack+ deletes them: `clean_autosaves` only removes
        `AutoSave` rows, and no other scheduled task touches the upload tree.

        So this reports rather than deletes, on purpose. A staged file is not
        necessarily abandoned: the autosave payload records `attachment_id` for
        upload tests, so an in-progress session a user can still resume - for
        AUTOSAVE_DAYS_TO_KEEP days, 30 by default - refers to exactly these
        rows. Anything that removes them has to respect that, and deciding the
        retention window is a site's call rather than this command's.
        """
        staged = [a for a in Attachment.objects.iterator() if not a.finalized]
        if not staged:
            self.stdout.write("No staged (unfinalized) attachments.")
            return

        now = timezone.now()
        keep_days = getattr(settings, "AUTOSAVE_DAYS_TO_KEEP", 30)
        total_bytes = 0
        older = 0
        oldest = None

        for attachment in staged:
            try:
                total_bytes += attachment.attachment.size
            except Exception:  # noqa: BLE001 - a staged file may be gone already
                pass
            created = getattr(attachment, "created", None)
            if created:
                if oldest is None or created < oldest:
                    oldest = created
                if (now - created).days > keep_days:
                    older += 1

        self.stdout.write(
            "%d staged (unfinalized) attachment(s), %.1f MiB, in %s."
            % (len(staged), total_bytes / (1024 * 1024), settings.TMP_UPLOAD_ROOT)
        )
        if oldest:
            self.stdout.write("  oldest: %s" % oldest.isoformat(timespec="seconds"))
        self.stdout.write(
            "  %d older than AUTOSAVE_DAYS_TO_KEEP (%d days), so referenced by no "
            "session a user could still resume." % (older, keep_days)
        )
        self.stdout.write(
            "Nothing removes these automatically. They are staging files, not "
            "records - unlike everything else under the media folder, which must "
            "never be deleted."
        )
