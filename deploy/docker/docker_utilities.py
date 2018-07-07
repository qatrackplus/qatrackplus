#    Copyright 2018 Simon Biggs

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""A set of utilities to manage the docker instance of qatrack
"""

import sys
import socket
import os
import io
import zipfile
import time
import datetime
import shutil
import pathlib
from glob import glob

import numpy as np

from django.contrib.auth.models import User
from django.core.management import call_command

DB_HOST = "qatrack-postgres"
DB_PORT = 5432

QATRACK_DIRECTORY = "/usr/src/qatrackplus"
MEDIA_DIRECTORY = os.path.join(QATRACK_DIRECTORY, "qatrack/media")
FIXTURES_GLOB = os.path.join(QATRACK_DIRECTORY, "fixtures/defaults/*/*")

DATA_DIRECTORY = os.path.join(QATRACK_DIRECTORY, "deploy/docker/user-data")
BACKUP_DIRECTORY = os.path.join(DATA_DIRECTORY, "backup-management/backups")
RESTORE_DIRECTORY = os.path.join(DATA_DIRECTORY, "backup-management/restore")

sys.path.append


def wait_for_postrgres():
    """Use this to wait for postgres to be ready
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            s.connect((DB_HOST, DB_PORT))
            s.close()
            break
        except socket.error as _:
            time.sleep(1)


def run_backup():
    """A method to backup qatrackplus, this needs to be rewritten to directly use postgres
    """

    pathlib.Path(BACKUP_DIRECTORY).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.fromtimestamp(
        time.time()).strftime('%Y%m%d%H%M%S')
    database_dump = io.StringIO()

    wait_for_postrgres()

    call_command('dumpdata', '--indent=2', '--exclude', 'auth.permission',
                 '--exclude', 'contenttypes', stdout=database_dump)

    backup_filepath = os.path.join(
        BACKUP_DIRECTORY, 'UTC_{}.zip'.format(timestamp))

    cwd = os.getcwd()
    os.chdir(MEDIA_DIRECTORY)

    with zipfile.ZipFile(backup_filepath, 'w') as backup_zip:
        backup_zip.writestr('database_dump.json', database_dump.getvalue())

        for dirname, _, files in os.walk('uploads'):
            backup_zip.write(dirname)
            for filename in files:
                backup_zip.write(os.path.join(dirname, filename))

    os.chdir(cwd)


def run_restore():
    """A method to restore a qatrackplus backup, this needs to be rewritten to directly use postgres
    """

    pathlib.Path(RESTORE_DIRECTORY).mkdir(parents=True, exist_ok=True)

    restore_filelist = glob(os.path.join(RESTORE_DIRECTORY, '*.zip'))

    if len(restore_filelist) == 1:
        restore_filepath = restore_filelist[0]

        call_command('flush', interactive=False)

        for root, _, files in os.walk(os.path.join(MEDIA_DIRECTORY, 'uploads')):
            for f in files:
                os.unlink(os.path.join(root, f))

        dirs_to_remove = glob(os.walk(os.path.join(MEDIA_DIRECTORY, 'uploads/*')))
        for directory in dirs_to_remove:
            shutil.rmtree(directory)

        with zipfile.ZipFile(restore_filepath, 'r') as restore_zip:
            restore_zip.extract('database_dump.json')

            for file in restore_zip.namelist():
                if file.startswith('uploads/'):
                    restore_zip.extract(
                        file, MEDIA_DIRECTORY)

        call_command('loaddata', 'database_dump.json', interactive=False)

        os.unlink('database_dump.json')

        call_command('migrate', interactive=False)

        os.unlink(restore_filepath)

    if len(restore_filelist) > 1:
        raise ValueError(
            'Only one restoration file should be placed within the restore directory')


def initialisation():
    """This function is passed to the django manage.py when the docker image boots
    """

    print('Waiting for postgres...')
    wait_for_postrgres()
    print('Connected to postgres')

    call_command('migrate', interactive=False)

    all_users = User.objects.all()
    # breakpoint here after upgraded to python 3.7
    print(len(all_users))

    if len(all_users) <= 1:
        admin_user = 'admin'
        admin_password = 'admin'
        admin_email = 'admin@example.com'

        User.objects.create_superuser(admin_user, admin_email, admin_password)

        fixtures = glob(FIXTURES_GLOB)
        for fixture in fixtures:
            call_command('loaddata', fixture)

    call_command('collectstatic', interactive=False)

    run_backup()
    run_restore()
