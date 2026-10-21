#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups"
MEDIA_DIR="/app_data/media"

# Open a lock file using file descriptor 9. The descriptor has no special
# meaning and will be closed automatically when this script terminates.
# The lock file is to prevent multiple simulteneous backups, or restoring
# during a backup.
exec 9>"$BACKUP_DIR/.qatrackplus-backup-restore.lock"

if ! flock --nonblock 9; then
    echo "Another backup or restore operation is already running." >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR" # If backup folder does not exist, create it. 
DATE=$(date +%Y%m%d_%H%M%S)
# How long the *backup archives* under /backups are kept. This is the only
# thing in this script that deletes anything, and it deletes only the archives
# it wrote itself - the db_*.dump and media_*.tar.gz pairs below.
#
# It must never be pointed at /app_data/media. The media folder is records: an
# attachment is part of the record of the work it is attached to, a corrected
# upload is stored beside the file it replaces rather than over it, and nothing
# in QATrack+ deletes one. A retention sweep over that tree would be deleting
# clinical records, and it would be deleting them silently.
RETENTION_DAYS=7

dump_file="$BACKUP_DIR/db_$DATE.dump"
temporary_dump_file="$dump_file.tmp"

media_file="$BACKUP_DIR/media_$DATE.tar.gz"
temporary_media_file="$media_file.tmp"

cleanup()
{
    rm -f "$temporary_dump_file" "$temporary_media_file"
}

# trap the EXIT signal:
# If this signal is emitted, cleanup() will run.
# This is to prevent .tmp files from accumulating in case a backup is failing
# repeatedly.
trap cleanup EXIT

echo "Starting backup at $DATE"

# Supply the database password to PostgreSQL client programs.
export PGPASSWORD="$POSTGRES_PASSWORD"

# Dump to a temporary file first. If pg_dump is interrupted, this prevents an
# incomplete archive from having the name of a completed backup.
echo "Dumping database..."

# --lock-wait-timeout: prevent pg_dump from waiting indefinitely for a conflicting
# database lock.
pg_dump \
    --host=postgres \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --format=custom \
    --lock-wait-timeout=60s \
    --file="$temporary_dump_file"

# Verify that pg_restore can actually read the dump.
echo "Checking dump file..."
pg_restore --list "$temporary_dump_file" >/dev/null

# Only rename the file to a valid file name after the dump has finished.
mv "$temporary_dump_file" "$dump_file"
echo "Successfully backed up DB to $dump_file"

# Archive the media files into a temporary file.
echo "Backing up media files..."
# This produces an archive whose files are relative to the root to the MEDIA_DIR
tar \
    --create \
    --gzip \
    --file="$temporary_media_file" \
    --directory="$MEDIA_DIR" \
    .

# Verify that tar can read the archive structure.
echo "Checking media archive..."
tar \
    --list \
    --gzip \
    --file="$temporary_media_file" \
    >/dev/null

mv "$temporary_media_file" "$media_file"
echo "Successfully backed up media files"

# Temporary files have either been renamed or removed. The trap is no longer
# needed, remove it.
trap - EXIT

# Cleanup old backups
find "$BACKUP_DIR" -type f -name "db_*.dump" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -type f -name "media_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup process completed successfully"
