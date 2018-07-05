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

sys.path.append('/usr/src/app/deploy/docker')
from docker_functions import wait_for_postrgres, run_backup, run_restore


wait_for_postrgres()


call_command('migrate', interactive=False)

all_users = User.objects.all()
if len(all_users) == 0:
    admin_user = os.getenv('ADMIN_USER', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')

    User.objects.create_superuser(admin_user, admin_email, admin_password)

    fixtures = glob('/usr/src/app/fixtures/defaults/*/*')
    for fixture in fixtures:
        call_command('loaddata', fixture)


call_command('collectstatic', interactive=False)


run_backup()
run_restore()



