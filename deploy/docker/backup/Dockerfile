FROM alpine:3.19

ARG HOST_UID=999
ARG HOST_GID=999

RUN apk add --no-cache postgresql-client bash tar dcron dos2unix procps

COPY backup.sh /backup.sh
RUN dos2unix /backup.sh && chmod +x /backup.sh

# Create volume mount point with matching UID/GID from Django
RUN mkdir -p /media && chown -R ${HOST_UID}:${HOST_GID} /media

# Setup cron job (runs daily at 2 AM)
RUN echo "0 2 * * * bash /backup.sh >> /var/log/backup.log 2>&1" > /etc/crontabs/root

CMD ["crond", "-f", "-d", "8"]
