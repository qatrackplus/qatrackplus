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
    # Ensure local_settings.py exists and uses docker_settings
    if [ ! -f qatrack/local_settings.py ]; then
        echo "from .docker_settings import *" > qatrack/local_settings.py
    fi

    VENV_PATH="deploy/docker/user-data/python-virtualenv"
    mkdir -p deploy/docker/user-data
    
    if [ -d "$VENV_PATH" ]; then
        VENV_PYTHON_VERSION=$("$VENV_PATH/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
        CURRENT_PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if [ "$VENV_PYTHON_VERSION" != "$CURRENT_PYTHON_VERSION" ]; then
            echo "Python version mismatch (Venv: $VENV_PYTHON_VERSION, Current: $CURRENT_PYTHON_VERSION). Recreating virtualenv..."
            rm -rf "$VENV_PATH"
        fi
    fi

    virtualenv "$VENV_PATH"
    source "$VENV_PATH/bin/activate"

    pip install ".[docker,postgres]"
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
