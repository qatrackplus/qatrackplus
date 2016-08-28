DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'qatrackplus',
        'USER': 'qatrackplus',
        'PASSWORD': 'qatrackplus',
        'HOST': '',
        'PORT': '',
    }
}

ALLOWED_HOSTS = ['*']
