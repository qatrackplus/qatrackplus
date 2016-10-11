DEBUG = False
TEMPLATE_DEBUG = DEBUG

SELENIUM_USE_CHROME = False

DATABASES = {
    'default': {
        'ENGINE': 'sql_server.pyodbc',
        'NAME': 'qatrackdb',
        'USER': 'sa',
        'PASSWORD': 'Password12!',
        'HOST': 'localhost\SQL2008R2SP2',
        'PORT': '',
        'OPTIONS': {
            'unicode_results': True
        }
    }
}

ALLOWED_HOSTS = ['*']
