#!/bin/bash
# Back up QATrack+'s database and uploaded files into /backups (deploy/docker/backups
# on the host). Runs nightly from cron; run it by hand with
#   docker compose exec backup backup
#
# Based on the backup script by @leducvin in qatrackplus#866.
set -euo pipefail

BACKUP_DIR="/backups"
MEDIA_DIR="/media"
LOCK_FILE="$BACKUP_DIR/.qatrackplus-backup-restore.lock"

# How many days of backups are kept: a backup is deleted once it is RETENTION_DAYS
# days old, so 7 keeps a week of nightly backups. This deletes only the db_*.dump
# and media_*.tar.gz files this script writes (and the .tmp files a killed backup
# leaves). Never point anything like it at the media folder: uploads are part of
# QATrack+'s records, and nothing in QATrack+ deletes one.
RETENTION_DAYS=7

# The backups hold everything in QATrack+, password hashes included, so only root
# may read them: everything this script creates is mode 600. Set here, before any
# file is created, so it holds however the script is started (cron, or docker
# exec, which can start it with umask 000).
umask 077

mkdir -p "$BACKUP_DIR"

# Make every backup in /backups readable by root only, including those made by
# earlier releases, which anyone on the server could read (mode 644, or 666). A
# folder that cannot hold Unix permissions (a Windows or network share) may
# refuse; a backup matters more than its permissions, so that is only a warning.
restrict_backups() {
    find "$BACKUP_DIR" -maxdepth 1 -type f \
        \( -name "db_*.dump" -o -name "media_*.tar.gz" -o -name "${LOCK_FILE##*/}" \) \
        ! -perm 600 -exec chmod 600 {} + ||
        echo "Warning: could not make every backup in $BACKUP_DIR readable by root only." >&2
}

# One backup or restore at a time: a restore must not run while a backup reads
# the database, and the nightly backup must not start during a restore.
exec 9>"$LOCK_FILE"
if ! flock --nonblock 9; then
    echo "Another backup or restore is already running." >&2
    exit 1
fi

restrict_backups

DATE=$(date +%Y%m%d_%H%M%S)
dump_file="$BACKUP_DIR/db_$DATE.dump"
media_file="$BACKUP_DIR/media_$DATE.tar.gz"

# Each archive is written under a .tmp name and renamed only once it is complete
# and readable, so an interrupted backup never leaves a file that looks finished.
cleanup() {
    rm -f "$dump_file.tmp" "$media_file.tmp"
}
trap cleanup EXIT

echo "Starting backup at $DATE"

# A backup killed outright (power cut, docker kill) cannot remove its own .tmp
# file. Holding the lock means no other backup is writing one now.
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name "db_*.dump.tmp" -o -name "media_*.tar.gz.tmp" \) -delete

export PGPASSWORD="$POSTGRES_PASSWORD"

echo "Dumping the database..."
# --lock-wait-timeout: give up rather than wait forever behind a conflicting lock.
pg_dump \
    --host=postgres \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --format=custom \
    --lock-wait-timeout=60s \
    --file="$dump_file.tmp"
# Read the whole archive back, every data block, not just its table of contents,
# so a dump cut short is caught now rather than on the day it is needed.
pg_restore --file=/dev/null "$dump_file.tmp"
mv "$dump_file.tmp" "$dump_file"
echo "Database saved to $dump_file"

echo "Archiving uploaded files..."
# Entries are media/..., the same layout as backups made by QATrack+ 4.0.
# .restore.* is restore-media's working folder, which a restore that was killed
# outright can leave behind; it is not part of the uploaded files.
tar --create --gzip --file="$media_file.tmp" --directory=/ \
    --anchored --exclude="${MEDIA_DIR#/}/.restore.*" "${MEDIA_DIR#/}"
tar --list --gzip --file="$media_file.tmp" >/dev/null
mv "$media_file.tmp" "$media_file"
echo "Uploaded files saved to $media_file"

trap - EXIT
restrict_backups

# find counts age in whole days, rounded down: -mtime +N matches files at least
# N+1 days old, so +$((RETENTION_DAYS - 1)) deletes those RETENTION_DAYS days old.
find "$BACKUP_DIR" -maxdepth 1 -type f -name "db_*.dump" -mtime +$((RETENTION_DAYS - 1)) -delete
find "$BACKUP_DIR" -maxdepth 1 -type f -name "media_*.tar.gz" -mtime +$((RETENTION_DAYS - 1)) -delete

echo "Backup completed successfully"
