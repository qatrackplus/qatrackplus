#!/bin/sh
# Run by compose.yaml's init service, as root, each time QATrack+ starts and
# before django does. QATrack+ runs as uid 1000, and installs from before 4.0.2
# ran it as root, so its volumes can hold root-owned files: this gives anything
# not already owned by QATrack+'s user to that user, then exits.
#
# QATRACK_MEDIA_DIR, QATRACK_LOGS_DIR and QATRACK_USER_DATA_DIR in .env can put
# a location in a folder on the server instead of a Docker volume. Handing over a
# folder cannot be undone, so, when any of them is set, this first refuses to
# start (and changes nothing) if:
#   - one location is inside another, or is the same folder (QATRACK_BACKUPS_DIR
#     included): the web server would show the logs or the secret key to anyone,
#     or the backups would be handed to QATrack+'s user;
#   - a folder holds something that is clearly not QATrack+'s data for that
#     location alone, marked or not: a .qatrackplus-data file below its top
#     (another of QATrack+'s folders, so the setting names a folder above the
#     one meant), or a file named like a backup (anywhere but among the
#     uploaded files, in media/uploads);
#   - a folder is not empty and has no .qatrackplus-data file to mark it as
#     QATrack+'s. An empty folder is marked here, so a new site needs no step.
# Docker volumes are always QATrack+'s own, so they are never checked or marked,
# and a site that sets none of the variables works exactly as before.
#
# A file with more than one name (a hard link) is never re-owned, in a folder or
# a volume: its other name can be anywhere on the same disk, and re-owning it
# would hand that file over too. It is left as it is, and a warning names it.
# QATrack+ itself never leaves a hard link in these locations.
#
# See "Keeping QATrack+'s data in folders on the server" in docs/install/docker.rst.
set -eu

uid=${QATRACK_UID:-1000}
gid=${QATRACK_GID:-1000}
marker=.qatrackplus-data
app=/usr/src/qatrackplus
media=$app/qatrack/media
static=$app/qatrack/static
user_data=$app/deploy/docker/user-data
logs=$app/logs
# Mounted read-only, only to check that nothing else is inside it.
backups=/backups
# The names backup.sh gives its archives, db_YYYYMMDD_HHMMSS.dump and
# media_YYYYMMDD_HHMMSS.tar.gz, with anything added after them: .tmp while
# backup.sh writes one, or .gz, .gpg and the like from a job that copies them.
d4='[0-9][0-9][0-9][0-9]'
stamp="${d4}${d4}_[0-9][0-9]${d4}"
# Uploaded files, which are not looked at for those names. QATrack+ keeps every
# uploaded file under media/uploads, and backups are never there. It adds the
# date and a random suffix to each name, but files uploaded before 2016 can
# keep the name they were uploaded with, whatever it was.
uploads=$media/uploads

# The .env setting (or "") behind a location, and the volume or folder used
# when it is unset.
setting_of() {
    case $1 in
        "$media") echo QATRACK_MEDIA_DIR ;;
        "$user_data") echo QATRACK_USER_DATA_DIR ;;
        "$logs") echo QATRACK_LOGS_DIR ;;
        "$backups") echo QATRACK_BACKUPS_DIR ;;
        *) echo "" ;;
    esac
}
default_of() {
    case $1 in
        "$media") echo "the media-volume Docker volume" ;;
        "$static") echo "the static-volume Docker volume" ;;
        "$user_data") echo "the user-data-volume Docker volume" ;;
        "$logs") echo "the logs-volume Docker volume" ;;
        "$backups") echo "the backups folder beside compose.yaml" ;;
    esac
}
# What QATrack+ keeps in a location, for messages.
what_of() {
    case $1 in
        "$media") echo "uploaded files" ;;
        "$user_data") echo "user data (its secret key)" ;;
        "$logs") echo "log files" ;;
    esac
}
# The folder on the server set for a location, or "" for the default.
folder_of() {
    setting=$(setting_of "$1")
    if [ -n "$setting" ]; then printenv "$setting" || true; fi
}
# How a location is named in messages: its setting and folder, or its volume.
describe() {
    folder=$(folder_of "$1")
    if [ -n "$folder" ]; then echo "$(setting_of "$1")=$folder"; else default_of "$1"; fi
}
# Path $2, inside location $1, as it is named on the server when the location is
# a folder there.
on_server() {
    folder=$(folder_of "$1")
    if [ -n "$folder" ]; then echo "$folder${2#"$1"}"; else echo "$2"; fi
}
# The first thing in location $1 that shows it is not QATrack+'s data for that
# location alone: a marker below its top (so it holds another of QATrack+'s
# folders, or a copy of one), or a file named like a backup outside the uploaded
# files. find stops at the first. restore-media's .restore.* working folders, at
# the top of the media folder, are QATrack+'s own and can hold the marker from a
# backup, so they are not looked in.
not_qatracks() {
    find "$1" -xdev -mindepth 1 \
        \( -path "$media/.restore.*" -prune \) -o \
        \( \( -path "$1/*/$marker" \
            -o \( ! -path "$uploads/*" \( -name "db_$stamp.dump*" -o -name "media_$stamp.tar.gz*" \) \) \) \
        -print -quit \)
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
problems=$tmp/problems
: >"$problems"
to_mark=

uses_folders=
for location in "$media" "$user_data" "$logs" "$backups"; do
    if [ -n "$(folder_of "$location")" ]; then uses_folders=yes; fi
done

if [ -n "$uses_folders" ]; then
    # Folders are compared by what they are on disk (device and inode), not by
    # the paths in .env, so relative paths such as ./backups and symbolic links
    # are handled too. A folder nested further down, on another disk mounted
    # inside a location, is not looked for (find -xdev).
    roots=$tmp/roots
    : >"$roots"
    for location in "$media" "$static" "$user_data" "$logs" "$backups"; do
        if [ -d "$location" ]; then
            printf '%s %s\n' "$(stat -c %d:%i "$location")" "$location" >>"$roots"
        fi
    done
    # The same folder used for two locations.
    awk 'seen[$1] { print seen[$1], $2 } { seen[$1] = $2 }' "$roots" |
        while read -r first second; do
            echo "$(describe "$second") is the same folder as $(describe "$first")." >>"$problems"
        done
    # One location inside another.
    while read -r _ outer; do
        find "$outer" -xdev -mindepth 1 -type d -printf '%D:%i\n' |
            awk -v roots="$roots" '
                BEGIN { while ((getline line < roots) > 0) { split(line, f, " "); inner[f[1]] = f[2] } }
                $1 in inner { print inner[$1] }' |
            while read -r inner; do
                echo "$(describe "$inner") is inside $(describe "$outer")." >>"$problems"
            done
    done <"$roots"
    if [ -s "$problems" ]; then
        cat >>"$problems" <<EOF
Give each of these locations a folder of its own, side by side, not one
inside another: the web server shows everything in the media folder to
anyone, and everything in the media, logs and user-data folders is given
to the QATrack+ user.
EOF
    fi

    # Folders must hold nothing that is clearly not QATrack+'s, and, unless they
    # are empty, must already be marked as QATrack+'s.
    for location in "$media" "$user_data" "$logs"; do
        folder=$(folder_of "$location")
        if [ -z "$folder" ]; then continue; fi
        found=$(not_qatracks "$location")
        if [ -n "$found" ]; then
            if [ "${found##*/}" = "$marker" ]; then
                why="another of QATrack+'s folders (a $marker file below its top)"
            else
                why="what looks like a QATrack+ backup"
            fi
            cat >>"$problems" <<EOF
$(setting_of "$location")=$folder
holds $why:
    $(on_server "$location" "$found")
It is not a folder of QATrack+'s $(what_of "$location") alone, so QATrack+ will
not use it, marked or not: each time it starts it gives everything in its
folders to its own user (uid $uid), which cannot be undone. Check the path
first: it may name a folder above the one you meant. Set it to the folder that
holds only QATrack+'s $(what_of "$location"), or to a new, empty one.
EOF
            continue
        fi
        if [ -f "$location/$marker" ] && [ ! -h "$location/$marker" ]; then continue; fi
        if [ -z "$(ls -A "$location")" ]; then
            to_mark="$to_mark $location"
            continue
        fi
        cat >>"$problems" <<EOF
$(setting_of "$location")=$folder
is not empty, and has no $marker file to mark it as QATrack+'s.
Each time QATrack+ starts it gives everything in its folders to its own user
(uid $uid), which cannot be undone, so it will not use a folder that may hold
anyone else's files. Check the path first: it may name the wrong folder, or a
folder above the one you meant. For a new site, choose an empty folder (Docker
creates one that does not exist yet). Only once you have checked that this
folder holds QATrack+'s $(what_of "$location") and nothing else (copied
from its volume, for example), mark it as QATrack+'s with:
    sudo touch $folder/$marker
EOF
    done
fi

if [ -s "$problems" ]; then
    {
        echo "QATrack+ did not start, and nothing was changed:"
        echo
        cat "$problems"
        echo
        echo "Fix .env and run docker compose up -d again. See \"Keeping QATrack+'s data in"
        echo "folders on the server\" in docs/install/docker.rst."
    } >&2
    exit 1
fi

for location in $to_mark; do
    cat >"$location/$marker" <<EOF
This folder holds QATrack+'s data ($(setting_of "$location") in deploy/docker/.env).
Each time QATrack+ starts, it gives everything in this folder to its own user.
Keep this file: without it, QATrack+ will not start with this folder.
EOF
    echo "Marked $(describe "$location") as QATrack+'s ($marker)."
done

# chown -h re-owns a symbolic link itself, never the file it points to (which
# may be outside the folder, or missing). -xdev keeps find off any other disk
# mounted inside a location: only the folder it is mounted on is re-owned,
# nothing on that disk. A file with more than one name (-links +1) is left
# alone: its other name may be outside the location, so someone who can write
# to a folder could link a file from elsewhere on the disk into it to be handed
# that file.
for location in "$media" "$static" "$user_data" "$logs"; do
    find "$location" -xdev \( ! -user "$uid" -o ! -group "$gid" \) \
        \( ! -type d -links +1 -fprintf "$tmp/linked" '%p\n' -fprintf "$tmp/linked_count" . \
        -o -printf . -exec chown -h "$uid:$gid" {} + \) >"$tmp/count"
    echo "Re-owned to $uid:$gid in $(describe "$location"): $(wc -c <"$tmp/count")"
    linked=$(wc -c <"$tmp/linked_count")
    if [ "$linked" -gt 0 ]; then
        {
            echo "Warning: not re-owned to $uid:$gid in $(describe "$location"):"
            echo "$linked file(s) with more than one name (a hard link). The other name may be"
            echo "outside it, and re-owning the file would hand that to QATrack+'s user too, so"
            echo "they are left as they are. QATrack+ never makes these; if one of them is"
            echo "QATrack+'s and it needs to change it, replace it with a copy of itself:"
            head -n 20 "$tmp/linked" | while IFS= read -r path; do
                echo "    $(on_server "$location" "$path")"
            done
            if [ "$linked" -gt 20 ]; then echo "    ..."; fi
        } >&2
    fi
done
