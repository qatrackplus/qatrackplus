FROM alpine:3

ARG HOST_UID=999
ARG HOST_GID=999

RUN apk add --no-cache postgresql-client bash tar dcron dos2unix procps flock

COPY backup.sh /usr/local/bin/backup
COPY restore-media.sh /usr/local/bin/restore-media
COPY restore-db.sh /usr/local/bin/restore-db

RUN dos2unix /usr/local/bin/* && chmod +x /usr/local/bin/*

# Create volume mount point with matching UID/GID from Django
RUN mkdir -p /app_data/media && chown -R ${HOST_UID}:${HOST_GID} /app_data/media

# Setup cron job (runs daily at 2 AM)
RUN echo "0 2 * * * /usr/local/bin/backup >> /var/log/backup.log 2>&1" > /etc/crontabs/root

CMD ["crond", "-f", "-d", "8"]
