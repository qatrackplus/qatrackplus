# QATrack+ Backup Wrapper
# The backup logic has been migrated to the Django `backup_site` management command
# to avoid duplicating database connection settings in multiple places.
#
# This script simply acts as a wrapper so that existing Windows Scheduled Tasks
# continue to work without modification.

$qatrack_dir = "C:\deploy\qatrackplus\"
$python_exe = "C:\deploy\venvs\qatrack40\Scripts\python.exe"

Set-Location $qatrack_dir
& $python_exe manage.py backup_site
