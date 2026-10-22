"""`backup_site` must archive the uploads whatever the database step did.

The database half returns early on PostgreSQL, on MySQL and on any engine it
does not implement. While the two halves were one method, that early return
skipped the uploads archive as well - so a PostgreSQL site that read "Please
use pg_dump" and arranged its own database dump still had no media backup, and
nothing said so. Raised by Copilot and CodeRabbit on PR crcrewso#18.
"""

import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock
from zipfile import ZipFile

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


class TestUploadsAreBackedUpIndependently(SimpleTestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.media = Path(self.root, "media")
        (self.media / "uploads").mkdir(parents=True)
        (self.media / "uploads" / "patient-qc.txt").write_text("x", encoding="utf-8")
        self.backups = Path(self.root, "backups")

    def _run(self, engine):
        databases = {"default": {"ENGINE": engine, "NAME": "qatrackplus"}}
        out = StringIO()
        with override_settings(
            DATABASES=databases,
            MEDIA_ROOT=str(self.media),
            BACKUP_DIR=str(self.backups),
        ):
            call_command("backup_site", stdout=out, stderr=StringIO())
        return out.getvalue()

    def _uploads_zips(self):
        return sorted(self.backups.glob("*/uploads.zip"))

    def test_postgresql_still_gets_its_uploads_archived(self):
        output = self._run("django.db.backends.postgresql")
        assert "pg_dump" in output, "the database half should still say what it cannot do"
        zips = self._uploads_zips()
        assert zips, "no uploads archive was written for a PostgreSQL site"
        assert "patient-qc.txt" in ZipFile(zips[0]).namelist()

    def test_mysql_still_gets_its_uploads_archived(self):
        self._run("django.db.backends.mysql")
        assert self._uploads_zips(), "no uploads archive was written for a MySQL site"

    def test_an_unimplemented_engine_still_gets_its_uploads_archived(self):
        self._run("django.db.backends.oracle")
        assert self._uploads_zips(), "no uploads archive was written"

    def test_a_missing_uploads_directory_is_not_a_failure(self):
        """A site with no uploads yet must not be stopped from rotating."""
        import shutil

        # postgresql, not sqlite3: the sqlite branch copies the database file
        # itself, which an overridden NAME does not point at.
        shutil.rmtree(self.media / "uploads")
        output = self._run("django.db.backends.postgresql")
        assert "does not exist" in output

    def test_an_unwritable_archive_is_reported(self):
        with mock.patch("shutil.make_archive", side_effect=OSError("disk full")):
            output = self._run("django.db.backends.postgresql")
        assert "Failed to back up uploads" in output
        assert "disk full" in output
