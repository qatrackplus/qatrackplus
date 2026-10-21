"""Sweeping staged attachments, and the boundary that keeps it safe.

The sweep boundary is AUTOSAVE_DAYS_TO_KEEP plus a margin, not the autosave
window itself: a session a user can still resume refers to its staged uploads
by id, so anything inside that window may still be wanted, and the margin
covers the clocks not lining up. Everything else under the media folder is
records and is never touched.
"""

from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from qatrack.attachments.models import Attachment


class TestCleanStagedAttachments(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("uploader", password="x")

    def _staged(self, days_old, name="abandoned.txt"):
        attachment = Attachment.objects.create(
            attachment=ContentFile(b"x" * 1024, name=name),
            label=name,
            created_by=self.user,
        )
        assert not attachment.finalized
        # `created` is auto_now_add, so it is set past the model.
        Attachment.objects.filter(pk=attachment.pk).update(
            created=timezone.now() - timezone.timedelta(days=days_old)
        )
        attachment.refresh_from_db()
        return attachment

    def _run(self, *args):
        out, err = StringIO(), StringIO()
        call_command("clean_staged_attachments", *args, stdout=out, stderr=err)
        return out.getvalue() + err.getvalue()

    @override_settings(AUTOSAVE_DAYS_TO_KEEP=30)
    def test_the_boundary_is_the_autosave_window_plus_the_margin(self):
        output = self._run()
        assert "AUTOSAVE_DAYS_TO_KEEP (30) + 7 = 37 days" in output, output

    @override_settings(AUTOSAVE_DAYS_TO_KEEP=14)
    def test_the_boundary_follows_the_setting(self):
        """A site that shortens its autosave window sweeps sooner."""
        assert "AUTOSAVE_DAYS_TO_KEEP (14) + 7 = 21 days" in self._run()

    @override_settings(AUTOSAVE_DAYS_TO_KEEP=30)
    def test_a_resumable_session_is_never_swept(self):
        """Inside the autosave window an upload may still be wanted."""
        recent = self._staged(days_old=29)
        self._run("--delete")
        assert Attachment.objects.filter(pk=recent.pk).exists()

    @override_settings(AUTOSAVE_DAYS_TO_KEEP=30)
    def test_the_margin_itself_is_not_swept(self):
        """35 days is past the autosave window but inside the margin."""
        in_margin = self._staged(days_old=35)
        self._run("--delete")
        assert Attachment.objects.filter(pk=in_margin.pk).exists()

    @override_settings(AUTOSAVE_DAYS_TO_KEEP=30)
    def test_past_the_boundary_is_swept(self):
        old = self._staged(days_old=40)
        path = old.attachment.path
        self._run("--delete")
        assert not Attachment.objects.filter(pk=old.pk).exists()
        import os
        assert not os.path.exists(path), "the row went but the file stayed"

    @override_settings(AUTOSAVE_DAYS_TO_KEEP=30)
    def test_it_reports_without_deleting_by_default(self):
        old = self._staged(days_old=40)
        output = self._run()
        assert Attachment.objects.filter(pk=old.pk).exists(), "a report deleted data"
        assert "Pass --delete" in output

    @override_settings(AUTOSAVE_DAYS_TO_KEEP=30)
    def test_a_finalized_attachment_is_never_a_candidate(self):
        """Records are not swept, however old they are.

        `finalized` is `has_owner and not is_in_tmp`, and giving the fixture a
        real owner means building a test list instance and everything under it.
        The guard being tested is the `finalized` check in the command, so the
        property is stood in for directly - the owned-and-moved combination it
        derives from is covered in `test_models.py`.
        """
        old = self._staged(days_old=400)
        with mock.patch.object(Attachment, "finalized", property(lambda self: True)):
            self._run("--delete")
        assert Attachment.objects.filter(pk=old.pk).exists()

    @override_settings(AUTOSAVE_DAYS_TO_KEEP=30)
    def test_the_margin_can_be_set(self):
        boundary = self._staged(days_old=35)
        self._run("--margin-days", "0", "--delete")
        assert not Attachment.objects.filter(pk=boundary.pk).exists()

    def test_a_negative_margin_is_refused(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self._run("--margin-days", "-1")
