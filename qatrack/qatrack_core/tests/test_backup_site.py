"""`backup_site` must not report a backup it did not take.

Three failures measured on real deployments are the reason these tests exist;
`backup_site.run_backup`'s docstring records each one. In short: SQL Server
printed success while writing nothing, SQLite wrote its copy outside the backup
directory, and PostgreSQL and MySQL returned before archiving the uploads.
"""

import os
import sqlite3
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

ENGINES_WITHOUT_A_DATABASE_BACKUP = [
    'mssql',
    'django.db.backends.postgresql',
    'django.db.backends.mysql',
]


def _db(engine, name='qatrackplus'):
    return {'default': {'ENGINE': engine, 'NAME': name}}


class BackupSiteTestCase(TestCase):

    def setUp(self):
        self.backup_dir = tempfile.mkdtemp()
        self.media_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.media_root, 'uploads'))
        with open(os.path.join(self.media_root, 'uploads', 'an-upload.txt'), 'w') as f:
            f.write('an uploaded file')

    def run_it(self, engine, name='qatrackplus'):
        out = StringIO()
        with override_settings(
            DATABASES=_db(engine, name), BACKUP_DIR=self.backup_dir,
            MEDIA_ROOT=self.media_root, BACKUP_WEEKLY_DAY=-1, BACKUP_MONTHLY_DAY=-1,
        ):
            call_command('backup_site', stdout=out)
        return out.getvalue()

    def backup_set(self):
        sets = [os.path.join(self.backup_dir, d) for d in os.listdir(self.backup_dir)]
        assert len(sets) == 1, sets
        return sets[0]


class TestItNeverClaimsADatabaseBackup(BackupSiteTestCase):

    def test_no_engine_without_support_is_told_a_backup_succeeded(self):
        for engine in ENGINES_WITHOUT_A_DATABASE_BACKUP:
            with self.subTest(engine=engine):
                output = self.run_it(engine)
                assert 'does not back up the database' in output
                assert 'Successfully backed up' not in output.replace(
                    'Successfully backed up uploads', '')

    def test_each_engine_is_pointed_at_its_own_tooling(self):
        assert 'pg_dump' in self.run_it('django.db.backends.postgresql')
        assert 'mysqldump' in self.run_it('django.db.backends.mysql')
        assert 'BACKUP DATABASE' in self.run_it('mssql')

    def test_no_database_file_appears_for_an_engine_it_cannot_back_up(self):
        self.run_it('django.db.backends.postgresql')
        written = os.listdir(self.backup_set())
        assert written == ['uploads.zip'], written


class TestTheDockerNoteIsConditional(BackupSiteTestCase):

    def test_postgres_gets_the_note_hedged(self):
        output = self.run_it('django.db.backends.postgresql')
        assert 'bundled `backup` service' in output
        assert 'if it is' in output

    def test_the_note_is_not_offered_to_engines_it_cannot_help(self):
        for engine in ('mssql', 'django.db.backends.mysql'):
            with self.subTest(engine=engine):
                assert 'bundled `backup` service' not in self.run_it(engine)


class TestUploadsAreBackedUpWhateverTheEngine(BackupSiteTestCase):
    """The old code returned before this step on PostgreSQL and MySQL."""

    def test_every_engine_gets_its_uploads_archived(self):
        for engine in ENGINES_WITHOUT_A_DATABASE_BACKUP:
            with self.subTest(engine=engine):
                self.setUp()
                output = self.run_it(engine)
                assert 'backed up uploads' in output
                assert os.path.exists(os.path.join(self.backup_set(), 'uploads.zip'))


class TestSQLiteIsBackedUpIntoTheBackupSet(BackupSiteTestCase):
    """The pathway works; it used to write to the wrong place."""

    def setUp(self):
        super().setUp()
        self.db_path = os.path.join(tempfile.mkdtemp(), 'qatrack.sqlite3')
        conn = sqlite3.connect(self.db_path)
        conn.execute('CREATE TABLE a_table (a_column text)')
        conn.execute("INSERT INTO a_table VALUES ('a row that must survive')")
        conn.commit()
        conn.close()

    def test_the_copy_lands_inside_the_backup_directory(self):
        output = self.run_it('django.db.backends.sqlite3', self.db_path)
        assert 'Backed up the SQLite database' in output
        expected = os.path.join(self.backup_set(), 'qatrack.sqlite3-script.bak')
        assert os.path.exists(expected), os.listdir(self.backup_set())
        assert not os.path.exists(self.db_path + '-script.bak'), \
            "the copy was written beside the live database again"

    def test_the_copy_is_a_readable_database_with_the_data_in_it(self):
        self.run_it('django.db.backends.sqlite3', self.db_path)
        copy = os.path.join(self.backup_set(), 'qatrack.sqlite3-script.bak')
        conn = sqlite3.connect(copy)
        try:
            rows = conn.execute('SELECT a_column FROM a_table').fetchall()
        finally:
            conn.close()
        assert rows == [('a row that must survive',)], rows

    def test_a_missing_database_file_is_reported_not_claimed(self):
        output = self.run_it('django.db.backends.sqlite3', '/nonexistent/qatrack.sqlite3')
        assert 'not a file on disk' in output
        assert 'Backed up the SQLite database' not in output
