# The same image as the `postgres` service in compose.yaml, so the client tools
# here can never be a different major version from the server they dump.
#
# `alpine:3` with the unpinned `postgresql-client` meta-package was installing
# PostgreSQL 18 client tools against the 15 server - checked, not guessed - and
# `postgresql15-client` is no longer available on current Alpine, so the version
# could not simply be pinned. Using the server's own image makes the two
# impossible to drift apart: change the postgres image and this follows.
FROM postgres:15-alpine

ARG HOST_UID=999
ARG HOST_GID=999

# postgresql-client is already in the base image at the server's exact version
RUN apk add --no-cache bash tar dcron dos2unix procps flock

COPY backup.sh /usr/local/bin/backup
COPY restore-media.sh /usr/local/bin/restore-media
COPY restore-db.sh /usr/local/bin/restore-db

RUN dos2unix /usr/local/bin/* && chmod +x /usr/local/bin/*

# Create volume mount point with matching UID/GID from Django
RUN mkdir -p /app_data/media && chown -R ${HOST_UID}:${HOST_GID} /app_data/media

# Setup cron job (runs daily at 2 AM)
RUN echo "0 2 * * * /usr/local/bin/backup >> /var/log/backup.log 2>&1" > /etc/crontabs/root

CMD ["crond", "-f", "-d", "8"]
