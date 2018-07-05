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

echo "Running Docker Init Script"
cp /usr/src/qatrackplus/deploy/docker/docker_settings.py /usr/src/qatrackplus/qatrack/local_settings.py
echo "import runpy; runpy.run_path(\"/usr/src/qatrackplus/deploy/docker/docker_utility_script.py\")" | python /usr/src/qatrackplus/manage.py shell

# /usr/bin/crontab deploy/docker/crontab
gunicorn qatrack.wsgi:application -w 2 -b :8000
