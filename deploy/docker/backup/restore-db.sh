#!/bin/bash
# Replace QATrack+'s database with a backup from /backups:
#   docker compose stop django django-q
#   docker compose run --rm --no-deps backup restore-db db_YYYYMMDD_HHMMSS.dump
#   docker compose up -d
#
# Based on the restore script by @leducvin in qatrackplus#866.
set -euo pipefail

BACKUP_DIR="/backups"
LOCK_FILE="$BACKUP_DIR/.qatrackplus-backup-restore.lock"
POSTGRES_HOST="postgres"
# The database restore-db connects to while it creates, renames and drops
# QATrack+'s: PostgreSQL cannot do those to the database a connection is using.
MAINTENANCE_DB="postgres"

# The only file this writes is the lock file in /backups; keep it root's, like
# the backups (see backup).
umask 077

if [ "$#" -ne 1 ]; then
    echo "Usage: restore-db db_YYYYMMDD_HHMMSS.dump" >&2
    echo "The backups are listed by: docker compose exec backup ls -lh /backups" >&2
    exit 2
fi
backup_name=$1

# A file name in /backups only, not a path.
if [ "$(basename "$backup_name")" != "$backup_name" ]; then
    echo "Give the name of a file in $BACKUP_DIR, not a path." >&2
    exit 1
fi
case "$backup_name" in
    db_*.dump) ;;
    *)
        echo "Not a database backup: $backup_name (expected db_*.dump)." >&2
        exit 1
        ;;
esac
backup_file="$BACKUP_DIR/$backup_name"
if [ ! -f "$backup_file" ]; then
    echo "No such backup: $backup_file" >&2
    exit 1
fi

: "${POSTGRES_USER:?POSTGRES_USER is not set}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set}"
: "${POSTGRES_DB:?POSTGRES_DB is not set}"
case "$POSTGRES_DB" in
    postgres | template0 | template1)
        echo "Refusing to replace PostgreSQL's own database: $POSTGRES_DB" >&2
        exit 1
        ;;
esac
# The backup is restored into a database of its own, which replaces QATrack+'s
# only once it is complete. Until then QATrack+'s database is not touched.
RESTORE_DB="${POSTGRES_DB}_restoring"
# Where QATrack+'s database is moved, for a moment, as the restored one takes
# its name. It is dropped straight after.
PREVIOUS_DB="${POSTGRES_DB}_before_restore"
# PostgreSQL cuts names longer than 63 bytes short, which could make these two
# names the same as QATrack+'s own.
if [ "$(printf '%s' "$PREVIOUS_DB" | wc -c)" -gt 63 ]; then
    echo "The database name \"$POSTGRES_DB\" is too long for restore-db (at most 48 characters)." >&2
    exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock --nonblock 9; then
    echo "Another backup or restore is already running." >&2
    exit 1
fi

export PGPASSWORD="$POSTGRES_PASSWORD"

# Run SQL from standard input against the maintenance database, stopping at the
# first error. The database names are passed as psql variables, so each is quoted
# correctly: :"name" as an identifier, :'name' as a string.
run_sql() {
    psql --host="$POSTGRES_HOST" --username="$POSTGRES_USER" --dbname="$MAINTENANCE_DB" \
        --no-psqlrc --quiet --tuples-only --no-align --set=ON_ERROR_STOP=1 \
        --set=live="$POSTGRES_DB" --set=restore="$RESTORE_DB" --set=previous="$PREVIOUS_DB"
}

drop_database() {
    # --force disconnects anyone still connected rather than waiting for them.
    # client_min_messages hides the notice --if-exists gives when there is none.
    PGOPTIONS="-c client_min_messages=warning" \
        dropdb --host="$POSTGRES_HOST" --username="$POSTGRES_USER" --maintenance-db="$MAINTENANCE_DB" \
        --if-exists --force "$1"
}

# Check everything that could fail before anything is changed.
echo "Checking the backup..."
# Read the whole archive, every data block, not just its table of contents, so a
# backup cut short is found now.
pg_restore --file=/dev/null "$backup_file"
echo "Checking the connection to PostgreSQL..."
existing=$(run_sql <<'SQL'
SELECT datname FROM pg_database WHERE datname IN (:'live', :'previous');
SQL
)
live_exists=false
if grep -qxF "$POSTGRES_DB" <<<"$existing"; then
    live_exists=true
fi
if grep -qxF "$PREVIOUS_DB" <<<"$existing"; then
    echo "A database called \"$PREVIOUS_DB\" is left over from an earlier restore that" >&2
    echo "was stopped part way. It may hold QATrack+'s data from before that restore." >&2
    echo "Once you are sure you do not need it, delete it with" >&2
    echo "  docker compose exec postgres dropdb --username=\"$POSTGRES_USER\" \"$PREVIOUS_DB\"" >&2
    echo "and run restore-db again. Nothing was changed." >&2
    exit 1
fi
if $live_exists; then
    live_size=$(run_sql <<<"SELECT pg_size_pretty(pg_database_size(:'live'));")
fi

echo
echo "This permanently replaces the database \"$POSTGRES_DB\" with:"
echo "  $backup_file"
echo
if $live_exists; then
    echo "The backup is restored beside the current database, which takes $live_size,"
    echo "so PostgreSQL needs at least that much free disk space while this runs."
    echo
fi
echo "Stop QATrack+ first (docker compose stop django django-q): anyone still"
echo "connected is disconnected, and anything saved now is lost."
echo
printf 'Type the database name "%s" to continue: ' "$POSTGRES_DB"
read -r confirmation
if [ "$confirmation" != "$POSTGRES_DB" ]; then
    echo "Database restore cancelled; nothing was changed."
    exit 1
fi

# Prints "yes" while the database being restored into still has its own name.
restore_db_exists() {
    run_sql <<<"SELECT CASE WHEN count(*) > 0 THEN 'yes' ELSE 'no' END FROM pg_database WHERE datname = :'restore';"
}

# Tell the admin where things stand if restore-db stops before it finishes, for
# any reason: an error, Ctrl-C or docker stop.
stage=restoring
on_exit() {
    local status=$?
    trap - EXIT INT TERM
    if [ "$stage" = swapping ]; then
        # The swap is one transaction, so it either happened or it did not.
        case $(restore_db_exists 2>/dev/null) in
            yes) stage=restoring ;;
            no) stage=swapped ;;
            *)
                echo >&2
                echo "restore-db stopped while it was putting the restored database in place, and" >&2
                echo "cannot reach PostgreSQL to check how far it got. If a database called" >&2
                echo "\"$RESTORE_DB\" still exists, nothing was changed; otherwise \"$POSTGRES_DB\"" >&2
                echo "holds the backup, and \"$PREVIOUS_DB\" (if it exists) the data from before." >&2
                exit "$status"
                ;;
        esac
    fi
    case $stage in
        restoring)
            echo >&2
            echo "The restore did not finish. The database \"$POSTGRES_DB\" was not changed." >&2
            drop_database "$RESTORE_DB" >/dev/null 2>&1 || true
            ;;
        swapped)
            $live_exists || exit "$status"
            echo >&2
            echo "The backup was restored, but the old copy of the database, now called" >&2
            echo "\"$PREVIOUS_DB\", was not deleted. Delete it with" >&2
            echo "  docker compose exec postgres dropdb --username=\"$POSTGRES_USER\" \"$PREVIOUS_DB\"" >&2
            ;;
    esac
    exit "$status"
}
trap on_exit EXIT
# Ctrl-C or docker stop: stop here, and let on_exit say where things stand.
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Restoring the backup into a new database, \"$RESTORE_DB\"..."
# One left over from a restore that was killed outright is only ever a copy of a
# backup, never QATrack+'s own data.
drop_database "$RESTORE_DB"
createdb --host="$POSTGRES_HOST" --username="$POSTGRES_USER" --maintenance-db="$MAINTENANCE_DB" \
    --owner="$POSTGRES_USER" --template=template0 "$RESTORE_DB"
# --single-transaction: a restore that fails part way stops there and leaves
# nothing behind. --no-owner: the restored tables belong to POSTGRES_USER,
# whatever user owned them where the backup was made.
pg_restore --host="$POSTGRES_HOST" --username="$POSTGRES_USER" --dbname="$RESTORE_DB" \
    --no-owner --single-transaction "$backup_file"

echo "Putting the restored database in place of \"$POSTGRES_DB\"..."
# One transaction: either the restored database takes QATrack+'s database's name
# and the old one is set aside, or nothing changes. A database cannot be renamed
# while anyone is connected to it, so disconnect them first; pg_terminate_backend
# waits up to 10 seconds for each connection to close.
if $live_exists; then
    set_aside='ALTER DATABASE :"live" RENAME TO :"previous";'
else
    set_aside=''
fi
stage=swapping
run_sql >/dev/null <<SQL
BEGIN;
SELECT pg_terminate_backend(pid, 10000) FROM pg_stat_activity
    WHERE datname IN (:'live', :'restore') AND pid <> pg_backend_pid();
$set_aside
ALTER DATABASE :"restore" RENAME TO :"live";
COMMIT;
SQL
stage=swapped

if $live_exists; then
    drop_database "$PREVIOUS_DB"
fi
stage=finished

echo "Database restored. Start QATrack+ again with: docker compose up -d"
