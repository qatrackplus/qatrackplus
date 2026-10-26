# PostgreSQL 16's client tools, pinned. QATrack+ 4.0's backup image (alpine:3.19)
# made its dumps with pg_dump 16, and pg_restore only reads dumps from its own
# version or older: PostgreSQL 15's cannot restore them ("unsupported version
# (1.15) in file header"). Version 16 tools back up and restore the postgres
# service's version 15 server. Never move this below the newest pg_dump that
# has made a site's backups; move it up with the postgres service.
#
# Only the client tools are installed, not the PostgreSQL server. compose.yaml
# runs this image with "init: true", so crond does not run as process 1.
FROM alpine:3.22

RUN apk add --no-cache postgresql16-client bash tar dcron dos2unix flock

COPY backup.sh /usr/local/bin/backup
COPY restore-db.sh /usr/local/bin/restore-db
COPY restore-media.sh /usr/local/bin/restore-media
# /backup.sh is where the backup script lived before; keep it working there.
RUN dos2unix /usr/local/bin/backup /usr/local/bin/restore-db /usr/local/bin/restore-media && \
    chmod 755 /usr/local/bin/backup /usr/local/bin/restore-db /usr/local/bin/restore-media && \
    ln -s /usr/local/bin/backup /backup.sh

# The media volume's mount point. Alpine ships /media with cdrom, floppy and usb
# folders, which Docker would copy into an empty media volume; start it empty.
RUN rm -rf /media && mkdir /media && chown 1000:1000 /media

# Back up every night at 2 AM
RUN echo "0 2 * * * /usr/local/bin/backup >> /var/log/backup.log 2>&1" > /etc/crontabs/root

CMD ["crond", "-f", "-d", "8"]
