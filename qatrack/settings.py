# Django settings for qatrack project.
import django.conf.global_settings as DEFAULT_SETTINGS
import os


#-----------------------------------------------------------------------------
#Debug settings - remember to set both DEBUG & TEMPLATE_DEBUG to false when
#deploying (either here or in local_settings.py)
DEBUG = True
TEMPLATE_DEBUG = True


#Who to email when server errors occur
ADMINS = (
    ('Admin Name', 'admin.email@yourplace.com'),
)
MANAGERS = ADMINS
SEND_BROKEN_LINK_EMAILS = True

#-----------------------------------------------------------------------------
#misc settings
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

VERSION = "0.2.1"

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'qatrack.wsgi.application'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '78kj_s=rqh46bsv10eb-)uyy02kr35jy19pp*7u$4-te=x0^86'
ROOT_URLCONF = 'qatrack.urls'

SITE_ID = 1
SITE_NAME = "QATrack+"

#-----------------------------------------------------------------------------
#Database settings

#if you wish to override the database settings below (e.g. for deployment),
#please do so here or in a local_settings.py file
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db/default.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.S
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

#----------------------------------------------------------------------------
#Default local settings

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Toronto'

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

FORMAT_MODULE_PATH = "qatrack.formats"

INPUT_DATE_FORMATS = (
    "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M",
    "%d-%m-%y %H:%M", "%d/%m/%y %H:%M",
)
SIMPLE_DATE_FORMAT = "%d-%m-%Y"
DATETIME_HELP = "Format DD-MM-YY hh:mm (hh:mm is 24h time e.g. 31-05-12 14:30)"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True


#----------------------------------------------------------------------------
#static media settings

#  Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT,"uploads")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT,"static")

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

#  Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, "admin_media"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)


#------------------------------------------------------------------------------
#Middleware
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'qatrack.middleware.login_required.LoginRequiredMiddleware',
    'qatrack.middleware.maintain_filters.FilterPersistMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

#for django-debug-toolbar
INTERNAL_IPS = ('127.0.0.1',)



#login required middleware settings
LOGIN_EXEMPT_URLS = [r"^accounts/",]
LOGIN_REDIRECT_URL = '/qa/unit/'
LOGIN_URL = "/accounts/login/"
ACCOUNT_ACTIVATION_DAYS = 7


#------------------------------------------------------------------------------
#Template settings
# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    #('django.template.loaders.cached.Loader', (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #)),
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT,"templates"),
    "genericdropdown/templates",
)

TEMPLATE_CONTEXT_PROCESSORS = list(DEFAULT_SETTINGS.TEMPLATE_CONTEXT_PROCESSORS)
TEMPLATE_CONTEXT_PROCESSORS += [
    'django.core.context_processors.request',
    "qatrack.context_processors.site",
]

#------------------------------------------------------------------------------
#Fixtures
#you can add more default fixture locations here
FIXTURE_DIRS = (
    'fixtures/',
)

#------------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'tastypie',

    'genericdropdown',
    'django_coverage',
    'debug_toolbar',

    'salmonella',

    'qatrack.accounts',
    'qatrack.units',
    'qatrack.qa',
    'qatrack.theme_bootstrap',
    'qatrack.data_tables',
    'qatrack.notifications',
    'qatrack.contacts',
]
#-----------------------------------------------------------------------------
#Session Settings
SESSION_COOKIE_AGE = 14*24*60*60

#-----------------------------------------------------------------------------
#Email and notification settings
EMAIL_NOTIFICATION_USER = None
EMAIL_NOTIFICATION_PWD = None
EMAIL_NOTIFICATION_TEMPLATE = "notification_email.txt"
EMAIL_NOTIFICATION_SENDER = "qatrack"
EMAIL_NOTIFICATION_SUBJECT = "QATrack+ Test Status Notification"

EMAIL_HOST = "" #e.g. 'smtp.gmail.com'
EMAIL_HOST_USER = '' # e.g. "randle.taylor@gmail.com"
EMAIL_HOST_PASSWORD = 'your_password_here'
EMAIL_USE_TLS = True
EMAIL_PORT = 587


#-----------------------------------------------------------------------------
#Account settings
#a list of group names to automatically add users to when they sign up
DEFAULT_GROUP_NAMES = [] # eg ["Therapists"]

#-----------------------------------------------------------------------------
#Authentication backend settings
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    #'qatrack.accounts.backends.ActiveDirectoryGroupMembershipSSLBackend',
)

#active directory settings (not required if only using ModelBackend
AD_DNS_NAME='' # e.g. ad.civic1.ottawahospital.on.ca

# If using non-SSL use these
AD_LDAP_PORT=389
AD_LDAP_URL='ldap://%s:%s' % (AD_DNS_NAME,AD_LDAP_PORT)

# If using SSL use these:
#AD_LDAP_PORT=636
#AD_LDAP_URL='ldaps://%s:%s' % (AD_DNS_NAME,AD_LDAP_PORT)

AD_SEARCH_DN = "" #eg "dc=ottawahospital,dc=on,dc=ca"
AD_NT4_DOMAIN= "" #Network domain that AD server is part of

AD_SEARCH_FIELDS= ['mail','givenName','sn','sAMAccountName','memberOf']
AD_MEMBERSHIP_REQ= [] # eg ["*TOHCC - All Staff | Tout le personnel  - CCLHO"]
#AD_CERT_FILE='/path/to/your/cert.txt'



#------------------------------------------------------------------------------
#Logging Settings

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
         'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
         },
         'console':{
              'level':'DEBUG',
              'class':'logging.StreamHandler',
          },
    },
    'loggers': {

        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'qatrack.console': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

PAGINATE_DEFAULT=50

#------------------------------------------------------------------------------
#Testing settings
TEST_RUNNER = 'django_coverage.coverage_runner.CoverageRunner'
COVERAGE_ADDITIONAL_MODULES = ["qatrack.tests"]

#------------------------------------------------------------------------------
#local_settings contains anything that should be overridden
#based on site specific requirements (e.g. deployment, development etc)
try:
    from local_settings import *
except ImportError:
    pass
