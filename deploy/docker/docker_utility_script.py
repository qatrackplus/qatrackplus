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

sys.path.append('/usr/src/qatrackplus/deploy/docker')
from docker_functions import wait_for_postrgres, run_backup, run_restore

print('Waiting for postgres...')
wait_for_postrgres()
print('Connected to postgres')

call_command('migrate', interactive=False)

all_users = User.objects.all()
print(len(all_users))

if len(all_users) <= 1:
    admin_user = 'admin'
    admin_password = 'admin'
    admin_email = 'admin@example.com'

    User.objects.create_superuser(admin_user, admin_email, admin_password)

    fixtures = glob('/usr/src/qatrackplus/fixtures/defaults/*/*')
    for fixture in fixtures:
        call_command('loaddata', fixture)


call_command('collectstatic', interactive=False)


run_backup()
run_restore()



