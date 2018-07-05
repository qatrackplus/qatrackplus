import sys
import socket
import os
import io
import zipfile
import time
import datetime
import shutil

import numpy as np

from glob import glob

from django.contrib.auth.models import User
from django.core.management import call_command


DB_HOST = "qatrack-postgres"
DB_PORT = 5432

def wait_for_postrgres():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            s.connect((DB_HOST, DB_PORT))
            s.close()
            break
        except socket.error as _:
            time.sleep(0.1)


def run_backup(backup_directory='/usr/src/app/deploy/docker/backup_management/backups'):    
    if not os.path.exists(backup_directory):
        os.makedirs(backup_directory)

    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S')
    database_dump = io.StringIO()
    
    wait_for_postrgres()
    
    call_command('dumpdata', '--indent=2', '--exclude', 'auth.permission', '--exclude', 'contenttypes', stdout=database_dump)

    backup_filepath = os.path.join(backup_directory, 'UTC_{}.zip'.format(timestamp))

    cwd = os.getcwd()
    os.chdir('/usr/src/app/qatrack/media')

    with zipfile.ZipFile(backup_filepath, 'w') as backup_zip:
        backup_zip.writestr('database_dump.json', database_dump.getvalue())
        
        for dirname, _, files in os.walk('uploads'):
            backup_zip.write(dirname)
            for filename in files:
                backup_zip.write(os.path.join(dirname, filename))
                
    os.chdir(cwd)
    
    
def run_restore(restore_directory='/usr/src/app/deploy/docker/backup_management/restore'):        
    if not os.path.exists(restore_directory):
        os.makedirs(restore_directory)
        

    restore_filelist = glob(os.path.join(restore_directory, '*.zip'))

    if len(restore_filelist) != 0:
        restore_filelist = np.sort(restore_filelist)
        restore_filepath = restore_filelist[-1]
        
        call_command('flush', interactive=False)
        
        for root, _, files in os.walk('/usr/src/app/qatrack/media/uploads'):
            for f in files:
                os.unlink(os.path.join(root, f))
                
        dirs_to_remove = glob('/usr/src/app/qatrack/media/uploads/*')
        for directory in dirs_to_remove:
            shutil.rmtree(directory)
        
        with zipfile.ZipFile(restore_filepath, 'r') as restore_zip:
            restore_zip.extract('database_dump.json')
            
            for file in restore_zip.namelist():
                if file.startswith('uploads/'):
                    restore_zip.extract(file, '/usr/src/app/qatrack/media/')

                
        call_command('loaddata', 'database_dump.json', interactive=False)
        
        os.unlink('database_dump.json')
        
        call_command('migrate', interactive=False)
        
        for f in restore_filelist:
            os.unlink(f)
