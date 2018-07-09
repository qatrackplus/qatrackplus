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

FROM python:3.6

RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ stretch-pgdg main' > /etc/apt/sources.list.d/pgdg.list
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
RUN apt-get update && apt-get install -y \
    cron postgresql-client-10 cifs-utils \
    && rm -rf /var/lib/apt/lists/*

RUN touch /root/.is_inside_docker
RUN touch /root/.is_hub_image

RUN mkdir /usr/src/qatrackplus
WORKDIR /usr/src/qatrackplus

RUN wget https://bitbucket.org/SimonGBiggs/qatrackplus/raw/simon-docker/requirements.postgres.txt
RUN wget https://bitbucket.org/SimonGBiggs/qatrackplus/raw/simon-docker/requirements.txt

RUN pip install --no-cache-dir virtualenv

RUN mkdir /root/virtualenv \
    && virtualenv  /root/virtualenv \
    && . /root/virtualenv/bin/activate \
    && pip install --no-cache-dir -r requirements.postgres.txt
