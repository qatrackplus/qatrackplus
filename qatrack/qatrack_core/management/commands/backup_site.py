import datetime
import glob
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


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
        """Back up the database and the uploads, and say whether both worked.

        The two steps are independent on purpose. They used to be one, and the
        database half returns early on PostgreSQL, on MySQL and on any engine
        it does not implement - so those sites got no uploads archive either,
        with nothing said about it. A site reading "Please use pg_dump" would
        reasonably take the rest of the backup to have happened. Raised by
        Copilot and CodeRabbit both on PR crcrewso#18.

        The return value still requires both, because it is what gates the
        retention step: nothing old is deleted on the strength of a backup that
        was not completely written.
        """
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        backup_loc = os.path.join(backup_dir, f"{today_str}-{backup_type}")

        if not os.path.exists(backup_loc):
            os.makedirs(backup_loc)

        database = self.backup_database(backup_loc, backup_type, db_name, today_str)
        uploads = self.backup_uploads(backup_loc)
        return database and uploads

    def backup_database(self, backup_loc, backup_type, db_name, today_str):
        # 1. Database Backup
        db_dir_override = self.get_setting('BACKUP_DB_DIR', None)
        
        if db_dir_override:
            # Construct the path using forward slashes for Linux/Docker environments
            sql_backup_loc = f"{db_dir_override}/{today_str}-{backup_type}"
            sql_backup_file = f"{sql_backup_loc}/{db_name}-script.bak"
        else:
            sql_backup_file = os.path.join(backup_loc, f"{db_name}-script.bak")

        local_backup_file = os.path.join(backup_loc, f"{db_name}-script.bak")
        
        if os.path.exists(local_backup_file):
            os.remove(local_backup_file)
            
        db_settings = settings.DATABASES['default']
        engine = db_settings['ENGINE']
        
        if 'mssql' in engine or 'sqlserver' in engine:
            query = f"BACKUP DATABASE [{db_name}] TO DISK='{sql_backup_file}'"
            connection.ensure_connection()
            old_autocommit = connection.get_autocommit()
            connection.set_autocommit(True)
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                self.stdout.write(self.style.SUCCESS(f"Successfully backed up SQL Server database to {sql_backup_file}"))
            except Exception as e:
                err_msg = str(e)
                self.stdout.write(self.style.ERROR(f"Failed to backup database: {err_msg}"))
                self.stdout.write(self.style.WARNING(
                    "\n[TIP] Docker or Remote DB Detected?\n"
                    "If SQL Server is running in Docker or on a remote server, it has a completely isolated filesystem "
                    "and cannot write to your local Windows drive directly.\n"
                    "To fix this:\n"
                    "1. Map your backup folder as a network share or Docker volume (e.g. `-v C:\\deploy\\backups:/backups`)\n"
                    "2. Add `BACKUP_DB_DIR = '/backups'` to your `local_settings.py` so the script uses the correct path format."
                ))
                return False
            finally:
                connection.set_autocommit(old_autocommit)
        elif 'postgresql' in engine:
            self.stdout.write(self.style.WARNING("PostgreSQL backup not natively implemented in this script yet. Please use pg_dump."))
            return False
        elif 'mysql' in engine:
            self.stdout.write(self.style.WARNING("MySQL backup not natively implemented in this script yet. Please use mysqldump."))
            return False
        elif 'sqlite3' in engine:
            db_path = db_settings['NAME']
            shutil.copy2(db_path, local_backup_file)
            self.stdout.write(self.style.SUCCESS(f"Copied SQLite database to {local_backup_file}"))
        else:
            self.stdout.write(self.style.WARNING(f"Database backup not implemented in this script for engine '{engine}'."))
            return False

        return True

    def backup_uploads(self, backup_loc):
        # 2. Uploads Zip
        uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        zip_file_path = os.path.join(backup_loc, 'uploads.zip')
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

        if not os.path.exists(uploads_dir):
            # Not a failure: a site that has never had an upload has nothing
            # here, and refusing to rotate old backups over that would be
            # wrong.
            self.stdout.write(self.style.WARNING(
                f"Uploads directory {uploads_dir} does not exist. Skipping uploads backup."
            ))
            return True

        try:
            shutil.make_archive(zip_file_path.replace('.zip', ''), 'zip', uploads_dir)
        except OSError as e:
            # Said out loud, and it costs the retention step, for the same
            # reason the database half does: a backup that is missing the
            # uploads must not license deleting an older one that has them.
            self.stdout.write(self.style.ERROR(f"Failed to back up uploads: {e}"))
            return False

        self.stdout.write(self.style.SUCCESS(f"Successfully backed up uploads to {zip_file_path}"))
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
