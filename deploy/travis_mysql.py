DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'qatrackplus',
        'USER': 'qatrackplus',
        'PASSWORD': 'qatrackplus',
        'HOST': '',
        'PORT': '',
    }
}

ALLOWED_HOSTS = ['*']
