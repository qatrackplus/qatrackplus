from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase


def _attachment(pk, finalized, file_exists, name="uploads/testlist/1/foo.bar", owner="Owner"):
    att = mock.Mock()
    att.pk = pk
    att.finalized = finalized
    att.file_exists = file_exists
    att.owner = owner
    att.attachment.name = name
    return att


class TestCheckAttachments(TestCase):

    def _run(self, attachments):
        manager = "qatrack.attachments.management.commands.check_attachments.Attachment.objects"
        out, err = StringIO(), StringIO()
        with mock.patch(manager) as objects:
            # The command builds its queryset via select_related(...).iterator().
            objects.select_related.return_value.iterator.return_value = iter(attachments)
            try:
                call_command("check_attachments", stdout=out, stderr=err)
                exit_code = 0
            except SystemExit as exc:
                exit_code = exc.code
        return exit_code, out.getvalue(), err.getvalue()

    def test_all_present(self):
        attachments = [_attachment(1, finalized=True, file_exists=True)]
        exit_code, out, err = self._run(attachments)
        assert exit_code == 0
        assert "All finalized attachment files are present." in out

    def test_missing_file_reported_and_nonzero(self):
        attachments = [
            _attachment(1, finalized=True, file_exists=True),
            _attachment(2, finalized=True, file_exists=False, name="uploads/testlist/1/gone.bar"),
        ]
        exit_code, out, err = self._run(attachments)
        assert exit_code == 1
        assert "gone.bar" in out
        assert "2\t" in out  # pk 2 (the missing one) is listed
        assert "1\t" not in out  # pk 1 (present) is not listed
        assert "missing their backing file" in err

    def test_storage_error_reported_and_nonzero(self):
        # A storage backend failure on one attachment must be reported and force a
        # non-zero exit, without crashing the audit or printing the missing table.
        class _StorageError:
            pk = 2
            finalized = True

            @property
            def file_exists(self):
                raise OSError("storage unavailable")

        exit_code, out, err = self._run([_StorageError()])
        assert exit_code == 1
        assert "Failed to check attachment 2: storage unavailable" in err
        assert "could not be checked due to storage errors" in err
        assert "pk\towner\tpath" not in out  # no missing table when only storage errors

    def test_unfinalized_excluded(self):
        # An unfinalized (tmp) attachment with a missing file must not be flagged.
        attachments = [_attachment(1, finalized=False, file_exists=False)]
        exit_code, out, err = self._run(attachments)
        assert exit_code == 0
        assert "All finalized attachment files are present." in out
