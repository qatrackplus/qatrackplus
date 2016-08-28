DEBUG = False
TEMPLATE_DEBUG = DEBUG

SELENIUM_VIRTUAL_DISPLAY = True
SELENIUM_USE_CHROME = False

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
