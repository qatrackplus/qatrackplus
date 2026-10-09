import datetime
import glob
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Backup QATrack+ database and media uploads'

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
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        backup_loc = os.path.join(backup_dir, f"{today_str}-{backup_type}")
        
        if not os.path.exists(backup_loc):
            os.makedirs(backup_loc)

        # 1. Database Backup - reported, not attempted.
        #
        # This command does not back up the database on any engine, and says so
        # per engine rather than appearing to succeed. The supported database
        # backup is the Docker `backup` service (`deploy/docker/backup/backup.sh`,
        # pg_dump); every other deployment uses its engine's own tooling as part
        # of the site's existing backup regime. See docs/install/backup.rst.
        #
        # PostgreSQL and MySQL already reported honestly. The two that did not
        # were measured and are why this block changed:
        #
        # - **SQL Server** ran `BACKUP DATABASE ... TO DISK` and printed
        #   "Successfully backed up SQL Server database to ..." even when the
        #   backup had failed. crane measured it on SQL Server 2022, 2026-10-08:
        #   exit 0, dated folders empty, 0 rows in `msdb.dbo.backupset`, and
        #   "Error: 3041 ... BACKUP failed to complete the command" in the server
        #   error log at the same second. The cursor was closed without draining
        #   BACKUP's result sets, and BACKUP streams progress as messages, so
        #   closing cancelled the batch. A backup command that reports success
        #   while writing nothing is worse than one that declines.
        #
        # - **SQLite** copied the database file, but to the wrong place and
        #   unsafely. `db_name` is an absolute path for SQLite, and
        #   `os.path.join(backup_loc, f"{db_name}-script.bak")` discards
        #   `backup_loc` when its second argument is absolute, so the copy landed
        #   beside the live database - on the same disk, outside BACKUP_DIR, and
        #   taken with `shutil.copy2` while QATrack+ may have been mid-write.
        #
        # Media is still backed up below, and that part works.
        db_settings = settings.DATABASES['default']
        engine = db_settings['ENGINE']

        if 'mssql' in engine or 'sqlserver' in engine:
            tool = "SQL Server's own BACKUP DATABASE, or SQL Server Management Studio"
        elif 'postgresql' in engine:
            tool = "pg_dump"
        elif 'mysql' in engine:
            tool = "mysqldump"
        elif 'sqlite3' in engine:
            tool = "a copy taken while QATrack+ is stopped, or sqlite3 .backup"
        else:
            tool = "the backup tooling for that engine"

        self.stdout.write(self.style.WARNING(
            f"Database backup is not performed by this command (engine: {engine}).\n"
            f"Use {tool}, or the Docker backup service, which is the supported path.\n"
            "See the Backup and Restore section of the documentation. Uploaded media "
            "is backed up below."
        ))

        # 2. Uploads Zip
        uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        zip_file_path = os.path.join(backup_loc, 'uploads.zip')
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
            
        if os.path.exists(uploads_dir):
            shutil.make_archive(zip_file_path.replace('.zip', ''), 'zip', uploads_dir)
            self.stdout.write(self.style.SUCCESS(f"Successfully backed up uploads to {zip_file_path}"))
        else:
            self.stdout.write(self.style.WARNING(f"Uploads directory {uploads_dir} does not exist. Skipping uploads backup."))

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
