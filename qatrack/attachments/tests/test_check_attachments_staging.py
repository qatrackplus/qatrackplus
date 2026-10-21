"""The staging report, because nothing removes staged attachments.

A file attached while performing QC is written to `uploads/tmp` with its
`Attachment` row created at once; both move into place only when the test list
instance is saved. Abandon the form and the pair stays. `clean_autosaves`
removes only `AutoSave` rows, and no other task touches the upload tree - so
the growth is invisible unless something reports it.
"""

from io import StringIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from qatrack.attachments.models import Attachment


class TestStagingReport(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("uploader", password="x")

    def _staged(self, name="abandoned.txt"):
        attachment = Attachment.objects.create(
            attachment=ContentFile(b"x" * 2048, name=name),
            label=name,
            created_by=self.user,
        )
        assert not attachment.finalized, "the fixture is not a staged attachment"
        return attachment

    def _run(self, *args):
        out, err = StringIO(), StringIO()
        try:
            call_command("check_attachments", *args, stdout=out, stderr=err)
        except SystemExit:
            pass
        return out.getvalue() + err.getvalue()

    def test_a_clean_installation_says_so(self):
        assert "No staged (unfinalized) attachments." in self._run("--staging")

    def test_staged_attachments_are_counted_and_measured(self):
        self._staged("one.txt")
        self._staged("two.txt")
        output = self._run("--staging")
        assert "2 staged (unfinalized) attachment(s)" in output, output
        assert "MiB" in output

    def test_the_report_says_nothing_removes_them(self):
        """The point of the report: this is not self-correcting."""
        self._staged()
        output = self._run("--staging")
        assert "Nothing removes these automatically" in output

    def test_the_report_distinguishes_staging_from_records(self):
        """Lest somebody read "never delete from media" and keep these too."""
        self._staged()
        output = self._run("--staging")
        assert "staging files, not" in output and "records" in output

    @override_settings(AUTOSAVE_DAYS_TO_KEEP=30)
    def test_recent_staging_is_not_counted_as_abandoned(self):
        """An autosave a user can still resume refers to these rows by id."""
        self._staged()
        output = self._run("--staging")
        assert "0 older than AUTOSAVE_DAYS_TO_KEEP (30 days)" in output, output

    def test_staging_is_not_reported_unless_asked(self):
        self._staged()
        assert "staged" not in self._run()
