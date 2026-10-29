import datetime
import glob
import os
import shutil
import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Back up QATrack+\'s uploaded media, and the database on SQLite. On other '
        'engines the database is not backed up and the command says which tool to use.'
    )

    def get_setting(self, name, default):
        return getattr(settings, name, default)

    def remove_old(self, backup_dir, backup_type, limit_date):
        # find files matching *-$backup_type
        pattern = os.path.join(backup_dir, f"*-{backup_type}")
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                # get creation time or modification time
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).date()
                if mtime < limit_date:
                    self.stdout.write(f"Removing old {backup_type} backup: {path}")
                    shutil.rmtree(path)

    def run_backup(self, backup_dir, backup_type, db_name):
        """Write what this command can write, and say plainly what it cannot.

        The rule here is that nothing is reported as backed up unless it is on
        disk afterwards. Three measured failures are why:

        - **SQL Server** ran ``BACKUP DATABASE ... TO DISK`` and printed
          "Successfully backed up" even when the backup had failed. Measured on
          SQL Server 2022, 2026-10-08: exit 0, the dated folder empty, no rows
          in ``msdb.dbo.backupset``, and "Error: 3041 ... BACKUP failed to
          complete the command" in the server error log at the same second. The
          cursor was closed without draining BACKUP's result sets, and BACKUP
          streams progress as messages, so closing it cancelled the batch. Until
          that is fixed and checked against a real instance, this command does
          not attempt it: declining is safer than claiming.

        - **SQLite** copied the database to the wrong place. ``db_name`` is an
          absolute path on SQLite, and ``os.path.join(backup_loc, f"{db_name}...")``
          discards ``backup_loc`` when its second argument is absolute, so the
          copy landed beside the live database - on the same disk, outside
          ``BACKUP_DIR``, where ``remove_old`` never pruned it. It is kept, with
          the path fixed, because the backup itself worked: measured 2026-10-28,
          the copy restored into an empty location with every row count intact.
          It is now taken through SQLite's own online backup API rather than
          ``shutil.copy2``, so it is consistent even if QATrack+ is running.

        - **PostgreSQL and MySQL** reported honestly but returned before the
          media step, so a site on either engine got an empty dated folder and
          no uploaded files at all. Media is now archived whatever the engine.
        """
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        backup_loc = os.path.join(backup_dir, f"{today_str}-{backup_type}")

        if not os.path.exists(backup_loc):
            os.makedirs(backup_loc)

        db_settings = settings.DATABASES['default']
        engine = db_settings['ENGINE']
        wrote_something = False

        if 'sqlite3' in engine:
            wrote_something = self.backup_sqlite(backup_loc, db_settings) or wrote_something
        else:
            self.report_no_database_backup(engine)

        if self.backup_uploads(backup_loc):
            wrote_something = True

        return wrote_something

    def backup_sqlite(self, backup_loc, db_settings):
        """Copy the SQLite database into the backup set, consistently."""
        db_path = str(db_settings['NAME'])
        if db_path == ':memory:' or not os.path.exists(db_path):
            self.stdout.write(self.style.WARNING(
                f"SQLite database {db_path} is not a file on disk; not backed up."
            ))
            return False

        # basename, not the full path: os.path.join discards backup_loc if the
        # second argument is absolute, which is what sent this file next to the
        # live database for every release before 4.0.2.
        target = os.path.join(backup_loc, f"{os.path.basename(db_path)}-script.bak")
        try:
            source = sqlite3.connect(db_path)
            try:
                destination = sqlite3.connect(target)
                try:
                    with destination:
                        source.backup(destination)
                finally:
                    destination.close()
            finally:
                source.close()
        except Exception as e:  # noqa: BLE001 - reported, not raised
            self.stdout.write(self.style.ERROR(f"Failed to back up the SQLite database: {e}"))
            if os.path.exists(target):
                os.remove(target)
            return False

        if not os.path.exists(target) or os.path.getsize(target) == 0:
            self.stdout.write(self.style.ERROR(
                f"SQLite backup {target} is missing or empty; treat this run as failed."
            ))
            return False

        self.stdout.write(self.style.SUCCESS(
            f"Backed up the SQLite database to {target} "
            f"({os.path.getsize(target)} bytes)"
        ))
        return True

    def report_no_database_backup(self, engine):
        """Say which tool to use, without implying anything was written."""
        if 'mssql' in engine or 'sqlserver' in engine:
            tool = "SQL Server's own BACKUP DATABASE, or SQL Server Management Studio"
        elif 'postgresql' in engine:
            tool = "pg_dump"
        elif 'mysql' in engine:
            tool = "mysqldump"
        else:
            tool = "the backup tooling for that engine"

        # Only a PostgreSQL deployment can be covered by the Docker `backup`
        # service, which runs pg_dump; and this command cannot see whether that
        # service is running, so the wording hedges rather than promises.
        docker_note = (
            "\nOn a Docker deployment the bundled `backup` service covers this - if it is "
            "running. This command cannot tell whether it is, so check that it has written "
            "a recent dump.\n"
            if 'postgresql' in engine else "\n"
        )
        self.stdout.write(self.style.WARNING(
            f"This command does not back up the database on this engine ({engine}).\n"
            f"Use {tool}.{docker_note}"
            "See the Backup and Restore section of the documentation. Uploaded media is "
            "backed up below."
        ))

    def backup_uploads(self, backup_loc):
        """Archive the uploaded files, on every engine."""
        uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        zip_file_path = os.path.join(backup_loc, 'uploads.zip')
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

        if not os.path.exists(uploads_dir):
            self.stdout.write(self.style.WARNING(
                f"Uploads directory {uploads_dir} does not exist. Skipping uploads backup."
            ))
            return False

        shutil.make_archive(zip_file_path.replace('.zip', ''), 'zip', uploads_dir)
        if not os.path.exists(zip_file_path):
            self.stdout.write(self.style.ERROR(
                f"Uploads archive {zip_file_path} was not written; treat this run as failed."
            ))
            return False
        self.stdout.write(self.style.SUCCESS(
            f"Successfully backed up uploads to {zip_file_path}"
        ))
        return True

    def handle(self, *args, **options):
        backup_dir = self.get_setting('BACKUP_DIR', 'C:\\deploy\\backups')
        weekly_day = self.get_setting('BACKUP_WEEKLY_DAY', 2) # 2 = Wednesday in Python (0=Mon)
        monthly_day = self.get_setting('BACKUP_MONTHLY_DAY', 3)
        
        days_to_keep = self.get_setting('BACKUP_DAYS_TO_KEEP', 7)
        weeks_to_keep = self.get_setting('BACKUP_WEEKS_TO_KEEP', 5)
        months_to_keep = self.get_setting('BACKUP_MONTHS_TO_KEEP', 12)
        
        db_name = settings.DATABASES['default'].get('NAME', 'qatrackplus')
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        today = datetime.date.today()

        # Monthly Backup
        if today.day == monthly_day:
            limit_date = today - datetime.timedelta(days=30 * months_to_keep)
            if self.run_backup(backup_dir, 'monthly', db_name):
                self.remove_old(backup_dir, 'monthly', limit_date)

        # Weekly Backup
        if today.weekday() == weekly_day:
            limit_date = today - datetime.timedelta(days=7 * weeks_to_keep)
            if self.run_backup(backup_dir, 'weekly', db_name):
                self.remove_old(backup_dir, 'weekly', limit_date)

        # Daily Backup
        limit_date = today - datetime.timedelta(days=days_to_keep)
        if self.run_backup(backup_dir, 'daily', db_name):
            self.remove_old(backup_dir, 'daily', limit_date)

        self.stdout.write(self.style.SUCCESS("Backup process completed."))
