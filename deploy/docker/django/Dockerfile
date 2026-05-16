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

FROM python:3.12-bookworm

RUN apt-get update && apt-get install -y \
    cron \
    postgresql-client \
    cifs-utils \
    dos2unix \
    chromium \
    build-essential \
    libpq-dev \
    python3-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN touch /root/.is_inside_docker

RUN pip install virtualenv

WORKDIR /usr/src/qatrackplus

# Ensure logs and media directories exist
RUN mkdir -p logs qatrack/media qatrack/static

EXPOSE 8000
