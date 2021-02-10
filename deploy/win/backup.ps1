#### Start Configuration Section #####################

# database name to backup
$db_name = "qatrackplus31"

# directory to place backups, should be remote directory if possible!
$backup_dir = "C:\deploy\backups\"
$qatrack_dir = "C:\deploy\qatrackplus\"  # root directory of QATrack+ installation

# day of week to create the weekly backup 0 = Sunday, 6 = Saturday
$weekly_backup_day = 3

# day of month to create the monthly backup
$monthly_backup_day = 3

# number of days to keep daily backups
$days_to_keep = 7

# number of weeks to keep weekly backups
$weeks_to_keep = 5

# number of months to keep monthly backups
$months_to_keep = 12


#### Stop Configuration Section #####################

function RunBackup($backup_type){

    # create backup directory
    $todays_date = Get-Date -UFormat "%Y-%m-%d"
    $backup_loc = "$backup_dir\$todays_date-$backup_type"
    New-Item -ItemType Directory -Force -Path $backup_loc

    # backup the database
    $backup_db_file = "$backup_loc\$db_name-script.bak"
    If(Test-path $backup_db_file) {Remove-item $backup_db_file}
    $query = "BACKUP DATABASE $db_name TO DISK='$backup_db_file'"
    Invoke-Sqlcmd -ServerInstance localhost –QUERY “$query"

    # now backup the uploads files
    $source = "$qatrack_dir\qatrack\media\uploads"
    $zip_file = "$backup_loc\uploads.zip"
    If(Test-path $zip_file) {Remove-item $zip_file}
    Add-Type -assembly "system.io.compression.filesystem"
    [io.compression.zipfile]::CreateFromDirectory($Source, $zip_file)

}

function RemoveOld($backup_type, $limit_date){
    # Delete files of $backup_type older than $limit_date.
    Get-ChildItem -Path "$backup_dir\*-$backup_type" -Force | Where-Object { $_.CreationTime -lt $limit_date } | Remove-Item -Force -Recurse
}

if ((Get-Date).Day -eq $monthly_backup_day){
    RemoveOld "monthly" (Get-Date).AddMonths(-1*$months_to_keep)
    RunBackup "monthly"
}

if ((Get-Date).DayOfWeek.value__ -eq $weekly_backup_day){
    RemoveOld "weekly" (Get-Date).AddDays(-7*$weeks_to_keep)
    RunBackup("weekly")
}

RemoveOld "daily" (Get-Date).AddDays(-1*$days_to_keep)
RunBackup "daily"
