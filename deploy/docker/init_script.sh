#!/bin/bash

echo "Running Docker Init Script"
cp /usr/src/qatrackplus/deploy/docker/docker_settings.py /usr/src/qatrackplus/qatrack/local_settings.py
echo "import runpy; runpy.run_path(\"/usr/src/qatrackplus/deploy/docker/docker_utility_script.py\")" | python /usr/src/qatrackplus/manage.py shell

# /usr/bin/crontab deploy/docker/crontab
gunicorn qatrack.wsgi:application -w 2 -b :8000
