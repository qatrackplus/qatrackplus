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

from glob import glob
import os

from django.contrib.auth.models import User
from django.core.management import call_command
import numpy as np

from docker_utilities import QATRACK_DIRECTORY, wait_for_postrgres

FIXTURES_GLOB: str = os.path.join(QATRACK_DIRECTORY, "fixtures/defaults/*/*")


def initialisation():
    """This function is passed to the django manage.py when the docker image
    boots
    """

    print('Waiting for postgres...')
    wait_for_postrgres()
    print('Connected to postgres')

    call_command('migrate', interactive=False)

    all_users = User.objects.all()
    is_superuser = [user.is_superuser for user in all_users]

    if not np.any(is_superuser):
        admin_user = 'admin'
        admin_password = 'admin'
        admin_email = 'admin@example.com'

        User.objects.create_superuser(admin_user, admin_email, admin_password)

        fixtures = sorted(glob(FIXTURES_GLOB))
        for fixture in fixtures:
            call_command('loaddata', fixture)

    call_command('collectstatic', interactive=False)
