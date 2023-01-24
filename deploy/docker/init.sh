#!/bin/bash

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

echo "init.sh"

/etc/init.d/cron start

# If using an image from docker-hub don't reinstall the pip requirements
if [ ! -f /root/.is_hub_image ]; then
    mkdir -p deploy/docker/user-data/python-virtualenv
    virtualenv deploy/docker/user-data/python-virtualenv
    source deploy/docker/user-data/python-virtualenv/bin/activate

    pip install -r requirements/docker.txt
else
    source /root/virtualenv/bin/activate
fi

path_append="
import sys
sys.path.append('/usr/src/qatrackplus/deploy/docker')
"

backup_restore="
$path_append
import docker_utilities
docker_utilities.run_backup()
docker_utilities.run_restore()
"

PGPASSWORD=postgres
echo "$backup_restore" | python

initialisation="
$path_append
import docker_initialisation
docker_initialisation.initialisation()
"

echo "$initialisation" | python /usr/src/qatrackplus/manage.py shell

python manage.py migrate
python manage.py createcachetable
chmod a+x deploy/docker/cron_backup.sh
/usr/bin/crontab deploy/docker/crontab
/etc/init.d/cron status

gunicorn qatrack.wsgi:application -w 2 -b :8000
