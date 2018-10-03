#!/bin/bash

# set to absolute path of main directory of your QATrack+ deployment. Don't forget trailing slash
QATRACK_DIR=

# set to absolute path of where you want to keep your backups. Don't forget trailing slash
BACKUP_DIR=

# database name to backup
DATABASE=

HOSTNAME=localhost

# username/PWD to use to access the database
USERNAME=qatrack
PASSWORD=qatrackpass

# backup uploaded files as well as the database
ENABLE_FILE_BACKUP=yes

# Which day to take the weekly backup from (1-7 = Monday-Sunday)
DAY_OF_WEEK_TO_KEEP=7

# Number of days to keep daily backups
DAYS_TO_KEEP=7

# How many weeks to keep weekly backups
WEEKS_TO_KEEP=5

# How many months to keep monthly backups
MONTHS_TO_KEEP=12

function perform_backups()
{
    SUFFIX=$1
    FINAL_BACKUP_DIR=$BACKUP_DIR"`date +\%Y-\%m-\%d`$SUFFIX/"

    echo "Making backup directory in $FINAL_BACKUP_DIR"

    if ! mkdir -p $FINAL_BACKUP_DIR; then
        echo "Cannot create backup directory in $FINAL_BACKUP_DIR." 1>&2
        exit 1;
    fi;


    echo "Custom backup of $DATABASE"

    if ! MYSQL_PWD=$PASSWORD mysqldump -h "$HOSTNAME" -u "$USERNAME" --databases "$DATABASE" | gzip > $FINAL_BACKUP_DIR"$DATABASE".gz.in_progress; then
        echo "[!!ERROR!!] Failed to produce backup database $DATABASE"
    else
        mv $FINAL_BACKUP_DIR"$DATABASE".gz.in_progress $FINAL_BACKUP_DIR"$DATABASE".gz
    fi

    if [ $ENABLE_FILE_BACKUP = "yes" ]
    then
        FILE_BACKUP_PATH=$FINAL_BACKUP_DIR"uploads.tar.gz"
        UPLOADS_DIR=$QATRACK_DIR"qatrack/media/uploads/"
        CSS_PATH=$QATRACK_DIR"qatrack/static/qatrack_core/css/site.css"
        echo "Backup of QATrack+ Uploads"
        tar cvf - $UPLOADS_DIR | gzip -9 - > $FILE_BACKUP_PATH
        cp $CSS_PATH $FINAL_BACKUP_DIR 2>/dev/null

    fi

    echo -e "\nDatabase backups complete!"
}

# MONTHLY BACKUPS

DAY_OF_MONTH=`date +%d`
EXPIRED_MONTH_DAYS=`expr $((($MONTHS_TO_KEEP * 30) + 1))`

if [ $DAY_OF_MONTH -eq 1 ];
then
    # Delete all expired monthly directories
    find $BACKUP_DIR -maxdepth 1 -mtime +$EXPIRED_MONTH_DAYS -name "*-monthly" -exec rm -rf '{}' ';'

    perform_backups "-monthly"

    exit 0;
fi

# WEEKLY BACKUPS

DAY_OF_WEEK=`date +%u` #1-7 (Monday-Sunday)
EXPIRED_DAYS=`expr $((($WEEKS_TO_KEEP * 7) + 1))`

if [ $DAY_OF_WEEK = $DAY_OF_WEEK_TO_KEEP ];
then
    # Delete all expired weekly directories
    find $BACKUP_DIR -maxdepth 1 -mtime +$EXPIRED_DAYS -name "*-weekly" -exec rm -rf '{}' ';'

    perform_backups "-weekly"

    exit 0;
fi

# DAILY BACKUPS

# Delete daily backups 7 days old or more
find $BACKUP_DIR -maxdepth 1 -mtime +$DAYS_TO_KEEP -name "*-daily" -exec rm -rf '{}' ';'

perform_backups "-daily"

