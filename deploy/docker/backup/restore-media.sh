#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups"
MEDIA_DIR="/app_data/media"

usage()
{
    echo "Usage: restore-media <media-backup.tar.gz>" >&2
    echo "Example: restore-media media_20261016_020000.tar.gz" >&2
    exit 2
}

# Accept a single argument
if [ "$#" -ne 1 ]; then
    usage
fi
backup_name=$1

# Accept only a filename located directly under BACKUP_DIR.
if [ "$(basename "$backup_name")" != "$backup_name" ]; then
    echo "Specify a filename under $BACKUP_DIR, not a path." >&2
    exit 1
fi

case "$backup_name" in
    media_*.tar.gz)
        ;;
    *)
        echo "Invalid media backup filename: $backup_name" >&2
        echo "Expected a filename matching media_*.tar.gz." >&2
        exit 1
        ;;
esac

backup_file="$BACKUP_DIR/$backup_name"

if [ ! -f "$backup_file" ]; then
    echo "Media backup does not exist: $backup_file" >&2
    exit 1
fi

if [ ! -d "$MEDIA_DIR" ]; then
    echo "Media directory does not exist: $MEDIA_DIR" >&2
    exit 1
fi

if [ ! -w "$MEDIA_DIR" ]; then
    echo "Media directory is not writable: $MEDIA_DIR" >&2
    exit 1
fi

# Create staging inside the media volume so that the final moves remain on the
# same filesystem.
# Make a unique temporary directory (.XXXXXX gets replaced by random alphanumeric characters)
staging_dir=$(mktemp -d "$MEDIA_DIR/.restore.XXXXXX")
extraction_dir="$staging_dir/extracted"
archive_list="$staging_dir/archive.list"

mkdir -p "$extraction_dir"

cleanup()
{
    rm -rf "$staging_dir"
}

trap cleanup EXIT  # ensure the temporary dir is deleted even if EXIT signal is caught.

echo "Checking media archive..."

# Reading the complete archive listing detects a truncated or unreadable
# archive before the current media files are modified.
tar \
    --list \
    --gzip \
    --file="$backup_file" \
    >"$archive_list"

if [ ! -s "$archive_list" ]; then
    echo "The media archive is empty: $backup_file" >&2
    exit 1
fi

# Reject absolute paths or parent-directory components before extraction.
while IFS= read -r archive_entry; do
    case "$archive_entry" in
        /*)
            echo "Unsafe absolute archive path: $archive_entry" >&2
            exit 1
            ;;
    esac

    case "/$archive_entry/" in
        */../*)
            echo "Unsafe parent-directory reference: $archive_entry" >&2
            exit 1
            ;;
    esac
done <"$archive_list"

archive_layout=""

# Archives made with:
#
# tar -czf archive.tar.gz -C / app_data/media/
#
# contain app_data/media/... paths.
#
# grep -Eq '^app_data/media/?$' "$archive_list": check that at least 1 entry in
# the archive list contains an entry representing the root of the media dir: app_data/media
#
# grep -Evq '^app_data/media(/|$)' "$archive_list": check that no entry falls outside
# of app_data/media
if grep -Eq '^app_data/media/?$' "$archive_list" \
    && ! grep -Evq '^app_data/media(/|$)' "$archive_list"; then
    archive_layout="app-data-media"

# Archives made with:
#
# tar -czf archive.tar.gz -C / media/
#
# contain media/... paths.
elif grep -Eq '^media/?$' "$archive_list" \
    && ! grep -Evq '^media(/|$)' "$archive_list"; then
    archive_layout="media"

# Archives made with:
#
# tar --create --gzip --file=archive.tar.gz \
#     --directory=/app_data/media .
#
# contain ./... paths.
elif ! grep -Evq '^\./' "$archive_list"; then
    archive_layout="contents-only"
else
    echo "Unrecognized media archive layout." >&2
    echo >&2
    echo "Expected all entries to be under one of:" >&2
    echo "  media/" >&2
    echo "  app_data/media/" >&2
    echo "  ./" >&2
    exit 1
fi

case "$archive_layout" in
    app-data-media)
        echo "Detected archive layout: app_data/media/"
        ;;
    media)
        echo "Detected archive layout: media/"
        ;;
    contents-only)
        echo "Detected content-only archive layout: ./"
        ;;
esac

echo "Extracting media archive into a staging directory..."

# With no archive members specified, tar extracts every member.
tar \
    --extract \
    --gzip \
    --file="$backup_file" \
    --directory="$extraction_dir"

case "$archive_layout" in
    app-data-media)
        restore_source="$extraction_dir/app_data/media"
        ;;
    media)
        restore_source="$extraction_dir/media"
        ;;
    contents-only)
        restore_source="$extraction_dir"
        ;;
esac

if [ ! -d "$restore_source" ]; then
    echo "Expected restore directory was not found: $restore_source" >&2
    exit 1
fi

echo
echo "WARNING: This will permanently replace all files under:"
echo "  $MEDIA_DIR"
echo
echo "Backup to restore:"
echo "  $backup_file"
echo
echo "Detected layout:"
echo "  $archive_layout"
echo
printf 'Type RESTORE to continue: '
read -r confirmation

if [ "$confirmation" != "RESTORE" ]; then
    echo "Media restore cancelled."
    exit 1
fi

echo "Removing existing media files..."

# Preserve the staging directory while removing everything else from the
# mounted media directory.
find "$MEDIA_DIR" \
    -mindepth 1 \
    -maxdepth 1 \
    ! -path "$staging_dir" \
    -exec rm -rf -- {} +

echo "Restoring media files..."

# '/.' copies the source directory's contents, including hidden files, without
# creating an additional media or app_data directory at the destination.
cp -a "$restore_source/." "$MEDIA_DIR/"

rm -rf "$staging_dir"
trap - EXIT

echo "Media restore completed successfully."
