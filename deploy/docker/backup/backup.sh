#!/bin/bash
set -euo pipefail



BACKUP_DIR="/backups"
mkdir -p $BACKUP_DIR # If backup folder does not exist, create it. 
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

echo "Starting backup at $DATE"

# Dump database
pg_dump -h postgres -U postgres -d qatrackplus -F c -f "$BACKUP_DIR/db_$DATE.dump"

# Tar media
tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" -C / media/

# Cleanup old backups
find "$BACKUP_DIR" -type f -name "db_*.dump" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -type f -name "media_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully"
