DEBUG = False
TEMPLATE_DEBUG = DEBUG

SELENIUM_VIRTUAL_DISPLAY = True
SELENIUM_USE_CHROME = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'qatrackplus.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

ALLOWED_HOSTS = ['*']
