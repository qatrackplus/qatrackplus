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

print('Running docker settings')

ALLOWED_HOSTS = ['localhost']

SECRET_FILEPATH = 'deploy/docker/user-data/secret_key.txt'

try:
    with open(SECRET_FILEPATH, 'r') as f:
        SECRET_KEY = f.read()
except IOError:
    import secrets

    SECRET_KEY = secrets.token_urlsafe(64)

    with open(SECRET_FILEPATH, 'w') as f:
        f.write(SECRET_KEY)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': "postgres",
        'USER': "postgres",
        'PASSWORD': "postgres",
        'HOST': "qatrack-postgres",
        'PORT': 5432
    }
}
