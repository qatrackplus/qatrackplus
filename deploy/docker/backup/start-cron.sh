#!/bin/bash
# Start crond, which runs the nightly backup at 4 AM (see the Dockerfile), and
# say in `docker compose logs backup` which time zone that 4 AM is in.
#
# compose.yaml sets TZ from TIME_ZONE in .env, the same setting QATrack+ uses,
# and to QATrack+'s own default when TIME_ZONE is not set. crond's schedule and
# the date and time in each backup's file name both follow TZ.
set -euo pipefail

# QATrack+'s default TIME_ZONE, in qatrack/settings.py and compose.yaml (a test
# checks they all match).
default_zone=America/Toronto

zone=${TZ:-}
if [ -z "$zone" ]; then
    echo "Warning: TZ is not set, so backups run at 4 AM UTC and are named in UTC." >&2
    echo "Start the backup service with docker compose, which sets it from TIME_ZONE in .env." >&2
elif [ ! -f "/usr/share/zoneinfo/${zone#:}" ]; then
    # The C library does not complain about a zone it does not know: it quietly
    # uses UTC instead.
    echo "Warning: \"$zone\" is not a time zone this container knows, so backups run" >&2
    echo "at 4 AM UTC and are named in UTC. Set TIME_ZONE in .env to a name from the" >&2
    echo "tz database, such as America/Toronto, then run: docker compose up -d" >&2
else
    echo "Backups run every night at 4 AM, $zone time (it is now $(date '+%Y-%m-%d %H:%M %Z'))."
fi

# compose.yaml takes TIME_ZONE from .env, or from the shell that ran docker
# compose, which wins. QATrack+ (and this container's TIME_ZONE) only read .env.
# So TIME_ZONE set in that shell, as well as or instead of in .env, would put the
# backups and QATrack+ on different clocks.
if [ -n "$zone" ]; then
    if [ -n "${TIME_ZONE:-}" ] && [ "$TIME_ZONE" != "$zone" ]; then
        echo "Warning: backups use TZ=$zone, but TIME_ZONE is $TIME_ZONE in .env. Was" >&2
        echo "TIME_ZONE also set in the shell that ran docker compose? Unset it there," >&2
        echo "then run: docker compose up -d" >&2
    elif [ -z "${TIME_ZONE:-}" ] && [ "$zone" != "$default_zone" ]; then
        echo "Warning: backups use TZ=$zone, but TIME_ZONE is not set in .env, so" >&2
        echo "QATrack+ uses $default_zone. Was TIME_ZONE set in the shell that ran" >&2
        echo "docker compose? Set it in .env instead, then run: docker compose up -d" >&2
    fi
fi

exec crond -f -d 8
