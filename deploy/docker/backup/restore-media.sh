#!/bin/bash
# Replace QATrack+'s uploaded files with a backup from /backups:
#   docker compose stop django django-q
#   docker compose run --rm restore-media media_YYYYMMDD_HHMMSS.tar.gz
#   docker compose up -d
#
# The restore-media service (compose.yaml) runs this with the media volume
# mounted writable at /media. The long-running backup service mounts it
# read-only, so the nightly backup can never change the uploaded files, and
# this refuses to run there.
#
# Based on the restore script by @leducvin in qatrackplus#866.
set -euo pipefail

BACKUP_DIR="/backups"
# The media volume, mounted writable by the restore-media service.
TARGET_DIR="/media"
LOCK_FILE="$BACKUP_DIR/.qatrackplus-backup-restore.lock"

# The lock file, and the staging folder that holds the unpacked uploaded files
# until they are swapped in, are root's alone. The restored files keep the owner
# and mode stored in the backup, whatever the umask (see the tar command below).
umask 077

if [ "$#" -ne 1 ]; then
    echo "Usage: restore-media media_YYYYMMDD_HHMMSS.tar.gz" >&2
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
    media_*.tar.gz) ;;
    *)
        echo "Not an uploaded-files backup: $backup_name (expected media_*.tar.gz)." >&2
        exit 1
        ;;
esac
backup_file="$BACKUP_DIR/$backup_name"
if [ ! -f "$backup_file" ]; then
    echo "No such backup: $backup_file" >&2
    exit 1
fi
# TARGET_DIR must be the media volume, mounted writable. Run in the backup
# service it is read-only; run with no volume at all, it is just the image's empty
# folder, and restored files would vanish with the container.
if ! awk -v dir="$TARGET_DIR" '$2 == dir { found = 1 } END { exit !found }' /proc/mounts \
    || [ ! -d "$TARGET_DIR" ] || [ ! -w "$TARGET_DIR" ]; then
    echo "The uploaded files are not mounted writable at $TARGET_DIR. Restore them with" >&2
    echo "  docker compose run --rm restore-media $backup_name" >&2
    exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock --nonblock 9; then
    echo "Another backup or restore is already running." >&2
    exit 1
fi

for leftover in "$TARGET_DIR"/.restore.*; do
    if [ -e "$leftover" ]; then
        echo "Note: ${leftover#"$TARGET_DIR"/} in the media volume is left over from a restore that was" >&2
        echo "stopped part way, and is left alone. It may hold the uploaded files from before" >&2
        echo "that restore: check what is in it before you delete it." >&2
    fi
done

# Unpack into a staging folder on the same volume first, so a damaged archive
# is found before any current file is touched, and so the files can be swapped
# by renaming them rather than copying. backup leaves .restore.* out of backups.
staging=$(mktemp -d "$TARGET_DIR/.restore.XXXXXX")
stage=checking
on_exit() {
    local status=$?
    trap - EXIT INT TERM
    if [ "$stage" = setting_aside ] || [ "$stage" = replacing ]; then
        echo >&2
        if put_back; then
            echo "The restore did not finish. The uploaded files were put back as they were." >&2
        else
            echo "The restore did not finish, and the uploaded files could not all be put back." >&2
            echo "The ones not put back are still in $staging/previous (the media volume's" >&2
            echo "${staging#"$TARGET_DIR"/}/previous folder), which has been kept. Move everything in it back" >&2
            echo "into the media volume by hand before you start QATrack+ or run restore-media again." >&2
            exit "$status"
        fi
    fi
    rm -rf "$staging"
    exit "$status"
}
trap on_exit EXIT
# Ctrl-C or docker stop: stop here, and let on_exit tidy up.
trap 'exit 130' INT
trap 'exit 143' TERM

# Move every entry directly inside $1 into $2, dot-files included. .restore.*
# folders (this restore's staging folder, or one left by a restore that was
# killed outright) are never moved. Stops at the first move that fails and
# returns non-zero: put_back runs inside an "if", where set -e does not apply,
# so the failure has to be returned by hand.
move_entries() {
    local entry
    find "$1" -mindepth 1 -maxdepth 1 ! -name '.restore.*' -print0 |
        while IFS= read -r -d '' entry; do
            mv -- "$entry" "$2/" || return 1
        done
}

# Undo a replacement that stopped part way: remove what had come from the backup
# (it is all still in the backup file), then move the earlier files back.
put_back() {
    if [ "$stage" = replacing ]; then
        find "$TARGET_DIR" -mindepth 1 -maxdepth 1 ! -name '.restore.*' -exec rm -rf -- {} + || return 1
    fi
    move_entries "$staging/previous" "$TARGET_DIR"
}

echo "Checking the backup..."
tar --list --gzip --file="$backup_file" >"$staging/archive.list"
# Backups made by QATrack+ hold media/... and nothing else. Refuse anything
# else, including absolute paths and .. components.
if ! grep -Eq '^media/?$' "$staging/archive.list" \
    || grep -Evq '^media(/|$)' "$staging/archive.list" \
    || grep -Eq '(^|/)\.\.(/|$)' "$staging/archive.list"; then
    echo "$backup_name is not a QATrack+ uploaded-files backup: its entries must all be under media/." >&2
    exit 1
fi
mkdir "$staging/extracted" "$staging/previous"
# A backup made before backup left out restore-media's staging folders may hold
# one; it is not part of the uploaded files. --same-permissions and --same-owner
# (tar's defaults when run as root, given here so nothing depends on that) give
# each file the mode and owner it had when it was backed up, not the umask above,
# so QATrack+ (uid 1000) can read and write them again.
tar --extract --gzip --file="$backup_file" --directory="$staging/extracted" \
    --same-permissions --same-owner --anchored --exclude='media/.restore.*'

echo
echo "This permanently replaces every uploaded file in QATrack+ with:"
echo "  $backup_file"
echo
echo "Stop QATrack+ first (docker compose stop django django-q), so nothing is"
echo "uploaded while the files are replaced."
echo
printf 'Type RESTORE to continue: '
read -r confirmation
if [ "$confirmation" != "RESTORE" ]; then
    echo "Restore of uploaded files cancelled; nothing was changed."
    exit 1
fi

echo "Replacing uploaded files..."
# Renames within one volume: each move is instant, and needs no space beyond the
# unpacked backup. The current files are set aside first, so a restore that stops
# part way can put them back.
stage=setting_aside
move_entries "$TARGET_DIR" "$staging/previous"
stage=replacing
move_entries "$staging/extracted/media" "$TARGET_DIR"
stage=finished
rm -rf "$staging"

echo "Uploaded files restored. Start QATrack+ again with: docker compose up -d"
echo "(its init service gives the restored files to the QATrack+ user)."
