from django.core.management.base import BaseCommand

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

    def handle(self, *args, **options):
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
