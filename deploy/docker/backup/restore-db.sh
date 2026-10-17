#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups"
POSTGRES_HOST="postgres"
MAINTENANCE_DB="postgres"

usage()
{
    echo "Usage: restore-db <database-backup.dump>" >&2
    echo "Example: restore-db db_20261016_020000.dump" >&2
    exit 2
}

# Accept a single argument
if [ "$#" -ne 1 ]; then
    usage
fi
backup_name=$1

# Accept only a filename located directly under BACKUP_DIR, not a path.
if [ "$(basename "$backup_name")" != "$backup_name" ]; then
    echo "Specify a filename under $BACKUP_DIR, not a path." >&2
    exit 1
fi

case "$backup_name" in
    db_*.dump)
        ;;
    *)
        echo "Invalid database backup filename: $backup_name" >&2
        echo "Expected a filename matching db_*.dump." >&2
        exit 1
        ;;
esac

backup_file="$BACKUP_DIR/$backup_name"

if [ ! -f "$backup_file" ]; then
    echo "Database backup does not exist: $backup_file" >&2
    exit 1
fi

# Ensure the required PostgreSQL environment variables are set and nonempty.
: "${POSTGRES_USER:?POSTGRES_USER is not set or is empty}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set or is empty}"
: "${POSTGRES_DB:?POSTGRES_DB is not set or is empty}"

# Do not allow the script to replace a system or maintenance database.
case "$POSTGRES_DB" in
    postgres | template0 | template1)
        echo "Refusing to replace protected database: $POSTGRES_DB" >&2
        exit 1
        ;;
esac

# The application database and maintenance database must be different because
# PostgreSQL cannot drop the database to which the command is connected.
if [ "$POSTGRES_DB" = "$MAINTENANCE_DB" ]; then
    echo "The application and maintenance databases must be different." >&2
    exit 1
fi

# Use a lock on the shared backup volume. This allows the normal backup
# container and one-off restore containers to coordinate with each other.
exec 9>"$BACKUP_DIR/.qatrackplus-backup-restore.lock"

if ! flock --nonblock 9; then
    echo "Another backup or restore operation is already running." >&2
    exit 1
fi

# Supply the password to PostgreSQL client programs.
export PGPASSWORD="$POSTGRES_PASSWORD"

echo "Checking database archive..."

# Verify that pg_restore can read the archive before modifying the database.
pg_restore \
    --list \
    "$backup_file" \
    >/dev/null

echo "Checking access to the PostgreSQL maintenance database..."

# Verify connectivity and credentials before dropping the application database.
psql \
    --host="$POSTGRES_HOST" \
    --username="$POSTGRES_USER" \
    --dbname="$MAINTENANCE_DB" \
    --no-psqlrc \
    --tuples-only \
    --command="SELECT 1;" \
    >/dev/null

echo
echo "WARNING: This operation will permanently replace the database:"
echo "  $POSTGRES_DB"
echo
echo "Backup to restore:"
echo "  $backup_file"
echo
echo "Maintenance database:"
echo "  $MAINTENANCE_DB"
echo
echo "Django and Django-Q should be stopped before continuing."
echo
printf 'Type the database name "%s" to continue: ' "$POSTGRES_DB"
read -r confirmation

if [ "$confirmation" != "$POSTGRES_DB" ]; then
    echo "Database restore cancelled."
    exit 1
fi

echo "Dropping database $POSTGRES_DB..."

# Connect through MAINTENANCE_DB because PostgreSQL cannot drop the database
# used by the administrative connection. --force terminates other connections
# to the application database before attempting to drop it.
dropdb \
    --host="$POSTGRES_HOST" \
    --username="$POSTGRES_USER" \
    --maintenance-db="$MAINTENANCE_DB" \
    --if-exists \
    --force \
    "$POSTGRES_DB"

echo "Creating database $POSTGRES_DB..."

# Create a clean database from template0 and make POSTGRES_USER its owner.
createdb \
    --host="$POSTGRES_HOST" \
    --username="$POSTGRES_USER" \
    --maintenance-db="$MAINTENANCE_DB" \
    --owner="$POSTGRES_USER" \
    --template=template0 \
    "$POSTGRES_DB"

echo "Restoring database $POSTGRES_DB..."

# --no-owner prevents restoration of ownership assignments from the source
# system. Restored objects will be owned by the connected POSTGRES_USER.
#
# --single-transaction causes the restore to be committed as one transaction.
# If restoration fails, PostgreSQL rolls back the transaction rather than
# leaving a partially restored database.
pg_restore \
    --host="$POSTGRES_HOST" \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --no-owner \
    --single-transaction \
    --verbose \
    "$backup_file"

echo "Database restore completed successfully."
