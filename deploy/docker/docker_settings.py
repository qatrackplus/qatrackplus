import sys

ALLOWED_HOSTS = ['localhost']

DEBUG = False

SECRET_FILEPATH = 'deploy/docker/secret_key.txt'

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

try:
    from .user_settings import *
except ImportError:
    pass
