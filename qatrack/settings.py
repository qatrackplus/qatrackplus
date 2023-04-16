""" settings.py

    Default settings for QATrack+

    isort:skip_file
"""

import datetime
import os
import sys

import matplotlib

matplotlib.use("Agg")

# -----------------------------------------------------------------------------
DEBUG = False
DEBUG_TOOLBAR = False

# Who to email when server errors occur
ADMINS = (
    ('Admin Name', 'YOUR_EMAIL_ADDRESS_GOES_HERE'),
)
MANAGERS = ADMINS
SEND_BROKEN_LINK_EMAILS = False

# -----------------------------------------------------------------------------
# misc settings
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

LOG_ROOT = os.path.join(PROJECT_ROOT, "..", "logs")

VERSION = "3.1.1.3"
BUG_REPORT_URL = "https://github.com/qatrackplus/qatrackplus/issues/new"
FEATURE_REQUEST_URL = BUG_REPORT_URL

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'qatrack.wsgi.application'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '78kj_s=rqh46bsv10eb-)uyy02kr35jy19pp*7u$4-te=x0^86'
ROOT_URLCONF = 'qatrack.urls'

SITE_ID = 1
SITE_NAME = "QATrack+"

# -----------------------------------------------------------------------------
# Database settings

# if you wish to override the database settings below (e.g. for deployment),
# please do so here or in a local_settings.py file
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3'
        'NAME': os.path.join(PROJECT_ROOT, '..', 'db/default.db'),  # db name Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.S
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# ----------------------------------------------------------------------------
# Default local settings

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


# formats for strptime/strftime
DATE_INPUT_FORMATS = ["%d %b %Y", "%Y-%m-%d"]
DATETIME_INPUT_FORMATS = [
    "%d %b %Y %H:%M",
    "%d %b %Y %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
]
TIME_INPUT_FORMATS = ["%H:%M", "%H:%M:%S", "%H:%M:%S.%f"]

DATETIME_FORMAT = "j M Y H:i"
DATE_FORMAT = "j M Y"
TIME_FORMAT = "H:i"


DATETIME_HELP = "Format DD MMM YYYY hh:mm (hh:mm is 24h time e.g. 31 May 2012 14:30)"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

CONSTANT_PRECISION = 8
DEFAULT_NUMBER_FORMAT = None


# This is the warning message given to the user when a test result is out of tolerance
# Override this setting in local_settings.py to a locally relevant warning message
DEFAULT_WARNING_MESSAGE = "Do not treat"

# ----------------------------------------------------------------------------
# static media settings

#  Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "media")

UPLOAD_PATH = "uploads"
TMP_UPLOAD_PATH = os.path.join(UPLOAD_PATH, "tmp")
UPLOAD_ROOT = os.path.join(MEDIA_ROOT, "uploads")
TMP_UPLOAD_ROOT = os.path.join(UPLOAD_ROOT, "tmp")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'
UPLOADS_URL = MEDIA_URL + 'uploads/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, "static")

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

#  Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, "admin_media"),
    # os.path.join(PROJECT_ROOT, 'static/'),
)
# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# add a site specific css file if one doesn't already exist
SITE_SPECIFIC_CSS_PATH = os.path.join(PROJECT_ROOT, "qatrack_core", "static", "qatrack_core", "css", "site.css")
if not os.path.isfile(SITE_SPECIFIC_CSS_PATH):
    with open(SITE_SPECIFIC_CSS_PATH, 'w') as f:
        f.write("/* You can place any site specific css in this file*/\n")


# ------------------------------------------------------------------------------
# Middleware
MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.RemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'qatrack.middleware.login_required.LoginRequiredMiddleware',
    'qatrack.middleware.maintain_filters.FilterPersistMiddleware',
]

# login required middleware settings
LOGIN_EXEMPT_URLS = [r"^favicon.ico$", r"^accounts/", r"api/*", r"^oauth2/*"]
ACCOUNT_ACTIVATION_DAYS = 7
LOGIN_REDIRECT_URL = '/qc/unit/'
LOGIN_URL = "/accounts/login/"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(PROJECT_ROOT, 'templates'),
            'genericdropdown/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': False,
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'qatrack.context_processors.site',
            ],
        },
    },
]

# ------------------------------------------------------------------------------
# Fixtures
# you can add more default fixture locations here
FIXTURE_DIRS = (
    'fixtures/defaults/qa',
    'fixtures/defaults/units',
)

# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_extensions',
    'django_q',
    'django_comments',
    'formtools',
    'django_filters',
    'rest_framework',
    'rest_framework_filters',
    'rest_framework.authtoken',
    'listable',
    'genericdropdown',
    'recurrence',
    'widget_tweaks',
    'dynamic_raw_id',
    'mptt',
    'django_mptt_admin',
    'qatrack.cache',
    'qatrack.accounts',
    'qatrack.units',
    'qatrack.qa',
    'qatrack.qatrack_core',
    'qatrack.notifications',
    'qatrack.contacts',
    'qatrack.issue_tracker',
    'qatrack.service_log',
    'qatrack.parts',
    'qatrack.faults',
    'qatrack.attachments',
    'qatrack.reports',
    'admin_views',
]


# ----------------------------------------------------------------------------
# API settings

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':
        ('rest_framework.authentication.TokenAuthentication', 'rest_framework.authentication.SessionAuthentication'),
    # Use Django's standard `django.contrib.auth` permissions
    'DEFAULT_SCHEMA_CLASS': 'qatrack.api.schemas.QATrackAutoSchema',
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.DjangoModelPermissions'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'DATETIME_INPUT_FORMATS': DATETIME_INPUT_FORMATS,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_FILTER_BACKENDS': ('rest_framework_filters.backends.RestFrameworkFilterBackend',),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/min',
        'testlistinstance': '500/min',
    },
}

# -----------------------------------------------------------------------------
# Password validation settings

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
]

# -----------------------------------------------------------------------------
# Cache settings

CACHE_UNREVIEWED_COUNT = 'unreviewed-count'
CACHE_UNREVIEWED_COUNT_USER = 'unreviewed-count-user'
CACHE_QA_FREQUENCIES = 'qa-frequencies'
CACHE_RTS_QA_COUNT = 'unreviewed-rts-qa'
CACHE_RTS_INCOMPLETE_QA_COUNT = 'incomplete-rts-qa'
CACHE_IN_PROGRESS_COUNT_USER = 'in-progress-count-users'
CACHE_UNREVIEWED_COUNT_USER_DICT = 'unreviewed-count-users'
CACHE_DEFAULT_SE_STATUS = 'default-se-status'
CACHE_SE_NEEDING_REVIEW_COUNT = 'se_needing_review_count'
CACHE_SL_NOTIFICATION_TOTAL = 'sl-notification-total'
CACHE_SERVICE_STATUS_COLOURS = 'service-status-colours'
CACHE_ACTIVE_UTCS_FOR_UNIT_ = 'active_utcs_for_unit_{}'
CACHE_AUTOREVIEW_RULESETS = "autoreviewrulesets"
CACHE_UNREVIEWED_FAULT_COUNT = "unreviewed-fault-count"

MAX_CACHE_TIMEOUT = None

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'qatrack_cache_table',
    }
}

# -----------------------------------------------------------------------------
# Session Settings
SESSION_COOKIE_AGE = 14 * 24 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

CSRF_COOKIE_NAME = 'csrftoken'


# needs to be set to True when running behind reverse proxy (normal deploy)
# set to False when not running behind reverse proxy
# Use True for e.g. CherryPy/IIS and False for Apache/mod_wsgi
USE_X_FORWARDED_HOST = False
HTTP_OR_HTTPS = "http"

# -----------------------------------------------------------------------------
# Email and notification settings
EMAIL_NOTIFICATION_USER = None
EMAIL_NOTIFICATION_PWD = None
EMAIL_NOTIFICATION_TEMPLATE = "notification_email.html"
EMAIL_NOTIFICATION_SENDER = "notifications@qatrackplus.com"
# use either a static subject or a customizable template
# EMAIL_NOTIFICATION_SUBJECT = "QATrack+ Test Status Notification"
EMAIL_NOTIFICATION_SUBJECT_TEMPLATE = "notification_email_subject.txt"

EMAIL_FAIL_SILENTLY = True
EMAIL_HOST = ""  # e.g. 'smtp.gmail.com'
EMAIL_HOST_USER = ''  # e.g. "randle.taylor@gmail.com"
EMAIL_HOST_PASSWORD = 'your_password_here'
EMAIL_USE_TLS = True
EMAIL_PORT = 587


# -----------------------------------------------------------------------------
# Account settings

# Authentication backend settings
AUTHENTICATION_BACKENDS = [
    'qatrack.accounts.backends.QATrackAccountBackend',
    # 'qatrack.accounts.backends.ActiveDirectoryGroupMembershipSSLBackend',
    # 'qatrack.accounts.backends.WindowsIntegratedAuthenticationBackend',
    # 'qatrack.accounts.backends.QATrackAdfsAuthCodeBackend',
]


ACCOUNT_ACTIVATION_DAYS = 7
ACCOUNTS_SELF_REGISTER = False
ACCOUNTS_CLEAN_USERNAME = None
ACCOUNTS_PASSWORD_RESET = True


# active directory settings (not required if only using ModelBackend
AD_DNS_NAME = ''  # e.g. ad.civic1.ottawahospital.on.ca

# If using non-SSL use these
AD_LDAP_PORT = 389
AD_LDAP_URL = 'ldap://%s:%s' % (AD_DNS_NAME, AD_LDAP_PORT)
AD_LDAP_USER = ''  # only used for WindowsIntegratedAuthenticationBackend
AD_LDAP_PW = ''  # only used for WindowsIntegratedAuthenticationBackend

AD_LU_ACCOUNT_NAME = "sAMAccountName"
AD_LU_MAIL = "mail"
AD_LU_SURNAME = "sn"
AD_LU_GIVEN_NAME = "givenName"
AD_LU_MEMBER_OF = "memberOf"

# If using SSL use these:
# AD_LDAP_PORT=636
# AD_LDAP_URL='ldaps://%s:%s' % (AD_DNS_NAME,AD_LDAP_PORT)

AD_SEARCH_DN = ""  # eg "dc=ottawahospital,dc=on,dc=ca"
AD_NT4_DOMAIN = ""  # Network domain that AD server is part of

AD_SEARCH_FIELDS = [AD_LU_MAIL, AD_LU_SURNAME, AD_LU_GIVEN_NAME, AD_LU_ACCOUNT_NAME, AD_LU_MEMBER_OF]

# If AD_MIRROR_GROUPS is True then a QATrack+ group will be created with the
# same name as the AD group if it doesn't exist.
AD_MIRROR_GROUPS = False


AD_CERT_FILE = ''  # AD_CERT_FILE = '/path/to/your/cert.txt'

CLEAN_USERNAME_STRING = AD_CLEAN_USERNAME_STRING = ''

# define a function called AD_CLEAN_USERNAME in local_settings.py if you
# wish to clean usernames before sending to ldap server
AD_CLEAN_USERNAME = None


# AD FS settings. For more information and other settings, see
# https://django-auth-adfs.readthedocs.io/en/latest/settings_ref.html
AUTH_ADFS = {
    "SERVER": "some.adfs.server.com",
    "CLIENT_ID": "qatrackplus",
    "RELYING_PARTY_ID": "https://your.qatrackserver.com",
    "AUDIENCE": "http://your.qatrackserver.com",
    "CLAIM_MAPPING": {
        "first_name": "given_name",
        "last_name": "family_name",
        "email": "email"
    },
    "USERNAME_CLAIM": "winaccountname",
    "GROUPS_CLAIM": "group",
}

# ------------------------------------------------------------------------------
# Logging Settings
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
def skip_requests(record):  # noqa: E302
    skip = (
        record.args[0].startswith("GET /static/") or
        record.args[0].startswith("GET /accounts/ping/")
    )
    return not skip


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        },
        'skip_requests': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': skip_requests,
        }
    },
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'CRITICAL',
            'filters': [],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOG_ROOT, "debug.log"),
            'backupCount': 26,  # how many backup file to keep, 10 days
            'formatter': 'verbose',
        },
        'migrate': {
            'level': 'INFO',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOG_ROOT, "migrate.log"),
            'backupCount': 26,  # how many backup file to keep, 10 days
            'formatter': 'verbose',
        },
        'django-q': {
            'level': 'INFO',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOG_ROOT, "django-q.log"),
            'backupCount': 26,  # how many backup file to keep, 10 days
            'formatter': 'verbose',
        },
        'auth': {
            'level': 'INFO',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOG_ROOT, "auth.log"),
            'backupCount': 1,  # how many backup file to keep, 10 days
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.utils.autoreload': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'mail_admins'],
            'filters': ['skip_requests'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'mail_admins', 'file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': [],  # Quiet by default!
            'propagate': False,
            'level': 'DEBUG',
        },
        'django.template': {
            'handlers': ['console', 'file', 'mail_admins'],
            'propagate': True,
            'level': 'WARNING',
        },
        'qatrack': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'qatrack.migrations': {
            'handlers': ['console', 'migrate', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django-q': {
            'handlers': ['console', 'django-q'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'auth.QATrackAccountBackend': {
            'handlers': ['console', 'auth'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'auth.ActiveDirectoryGroupMembershipSSLBackend': {
            'handlers': ['console', 'auth'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django_auth_adfs': {
            'handlers': ['console', 'auth'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

FORCE_SCRIPT_NAME = None

# ------------------------------------------------------------------------------
# QA Settings

# remember to change iDisplayLength in unittestcollection.js and
# testlistinstance.js if you change this
PAGINATE_DEFAULT = 50

NHIST = 5  # number of historical test results to show when reviewing/performing qa

PING_INTERVAL_S = 5  # how often to ping server when performing QA. Set to 0 to disable ping

ICON_SETTINGS = {
    'SHOW_STATUS_ICONS_PERFORM': True,
    'SHOW_STATUS_ICONS_LISTING': True,
    'SHOW_STATUS_ICONS_REVIEW': True,
    'SHOW_STATUS_ICONS_HISTORY': False,
    'SHOW_REVIEW_ICONS': True,
    'SHOW_REVIEW_LABELS_LISTING': True,
    'SHOW_STATUS_LABELS_LISTING': True,
    'SHOW_STATUS_LABELS_REVIEW': True,
    'SHOW_DUE_ICONS': True,
}

# Only show first display of category when multiple tests are shown
# sequentially with the same category
CATEGORY_FIRST_OF_GROUP_ONLY = False
CHOOSE_UNIT_CATEGORY_DROPDOWN = False

# Display ordering on the "Choose Unit" page. (Use "name" or "number")
ORDER_UNITS_BY = "number"

# Enable or disable the "Difference" column when reviewing test lists
REVIEW_DIFF_COL = False

# Enable bulk review on Unreviewed pages
REVIEW_BULK = True

# default display settings for test statuses
TEST_STATUS_DISPLAY = {
    'fail': "Fail",
    'not_done': "Not Done",
    'done': "Done",
    'ok': "OK",
    'tolerance': "Tolerance",
    'action': "Action",
    'no_tol': "No Tol Set",
}

# default short display settings for test statuses
TEST_STATUS_DISPLAY_SHORT = {
    'fail': "Fail",
    'not_done': "Not Done",
    'done': "Done",
    'ok': "OK",
    'tolerance': "TOL",
    'action': "ACT",
    'no_tol': "NO TOL",
}

DEFAULT_COLOURS = [
    'rgba(60,141,188,1)',
    'rgba(0,192,239,1)',
    'rgba(0,166,90,1)',
    'rgba(0,166,90,1)',
    'rgba(243,156,18,1)',
    'rgba(245,105,84,1)',
    'rgba(210,214,222,1)',
    'rgba(0,31,63,1)',
    'rgba(240,245,2,1)',
    'rgba(57,204,204,1)',
    'rgba(96,92,168,1)',
    'rgba(216,27,96,1)',
    'rgba(1,255,112,1)',
    'rgba(17,17,17,1)',
]
DEFAULT_TEST_STATUS_COLOUR = 'rgba(243,156,18,1)'

USE_ISSUES = False  # internal development issue tracker

DELETE_REASONS = (
    ('Duplicate', 'Duplicate'),
    ('Invalid', 'Invalid')
)

DEFAULT_AVAILABLE_TIMES = {
    'hours_sunday': datetime.timedelta(hours=0, minutes=0),
    'hours_monday': datetime.timedelta(hours=8, minutes=0),
    'hours_tuesday': datetime.timedelta(hours=8, minutes=0),
    'hours_wednesday': datetime.timedelta(hours=8, minutes=0),
    'hours_thursday': datetime.timedelta(hours=8, minutes=0),
    'hours_friday': datetime.timedelta(hours=8, minutes=0),
    'hours_saturday': datetime.timedelta(hours=0, minutes=0),
}

PARTS_ALLOW_BLANK_PART_NUM = False

TESTPACK_TIMEOUT = 30

# maximum line length for formatting of calculation procedures
COMPOSITE_AUTO_FORMAT = True
COMPOSITE_MAX_LINE_LENGTH = 88

AUTOSAVE_DAYS_TO_KEEP = 30

MAX_TESTS_PER_TESTLIST = 250
# SQL Explorer Settings

USE_SQL_REPORTS = False

EXPLORER_CONNECTIONS = {'Default': 'readonly'}
EXPLORER_DEFAULT_CONNECTION = 'readonly'
EXPLORER_SCHEMA_INCLUDE_TABLE_PREFIXES = ['auth_', 'qa', 'service_log', 'units', 'parts']
EXPLORER_SCHEMA_EXCLUDE_TABLE_PREFIXES = ['authtoken', 'sessions_']
EXPLORER_TASKS_ENABLED = False
EXPLORER_ASYNC_SCHEMA = False
EXPLORER_SQL_BLACKLIST = ['ALTER', 'RENAME ', 'DROP', 'TRUNCATE', 'INSERT INTO', 'UPDATE', 'REPLACE', 'DELETE', 'ALTER', 'CREATE TABLE', 'SCHEMA', 'GRANT', 'OWNER TO']  # noqa: E501


def EXPLORER_PERMISSION_CHANGE(request):
    return request.user.has_perm("reports.can_create_sql_reports")


def EXPLORER_PERMISSION_VIEW(request):
    return request.user.has_perm("reports.can_run_sql_reports")


if os.path.exists('/root/.is_inside_docker') and 'TRAVIS' not in os.environ:
    from .docker_settings import *  # NOQA


CHROME_PATH = ""
if os.name.lower() == "nt":
    user = os.getlogin()
    chrome_paths = [
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Documents and Settings\%s\Local Settings\Application Data\Google\Chrome\Application\chrome.exe' % user,
        r'C:\Program Files (x86)\Google\Application\chrome.exe',
        r'C:\Documents and Settings\%s\Local Settings\Application Data\Google\Chrome\chrome.exe' % user,
    ]
else:
    # unfortunately in Ubuntu 20, chromium is installed as a snap and won't
    # run headless as the www-data user.  Use Google Chrome instead
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]


for path in chrome_paths:
    if os.path.exists(path):
        CHROME_PATH = path


# ------------------------------------------------------------------------------
# local_settings contains anything that should be overridden
# based on site specific requirements (e.g. deployment, development etc)

from .local_settings import *  # noqa: F403, F401, E402


TEMPLATES[0]['OPTIONS']['debug'] = DEBUG


_MAX_FIELDS_PER_TEST = 5  # value, json_value, user_attached, skipped, extra value for bool
DATA_UPLOAD_MAX_NUMBER_FIELDS = max(MAX_TESTS_PER_TESTLIST * _MAX_FIELDS_PER_TEST, 1000)


# ------------------------------------------------------------------------------
# Directory availability & dependent paths

# Make any paths available that are not already created
# Also set file paths that are dependent on other settings which may be overridden
# in local_settings.py

UPLOAD_ROOT = os.path.join(MEDIA_ROOT, "uploads")
TMP_UPLOAD_ROOT = os.path.join(UPLOAD_ROOT, "tmp")
TMP_REPORT_ROOT = os.path.join(MEDIA_ROOT, "reports")

for d in (MEDIA_ROOT, UPLOAD_ROOT, TMP_UPLOAD_ROOT, LOG_ROOT, TMP_REPORT_ROOT):
    if not os.path.isdir(d):
        os.mkdir(d)

CACHE_LOCATION = os.path.join(PROJECT_ROOT, "cache", "cache_data")
IS_FILE_CACHE = CACHES['default']['BACKEND'] == 'django.core.cache.backends.filebased.FileBasedCache'
if IS_FILE_CACHE and not os.path.isdir(CACHE_LOCATION):
    os.mkdir(CACHE_LOCATION)


if FORCE_SCRIPT_NAME:
    # Fix URL for Admin Views if FORCE_SCRIPT_NAME_SET in local_settings
    ADMIN_VIEWS_URL_PREFIX = FORCE_SCRIPT_NAME + "/admin"


# no longer using EMAIL_NOTIFICATION_USER/PWD but people may have
# notification specific settings set.
if EMAIL_NOTIFICATION_USER and not EMAIL_HOST_USER:
    EMAIL_HOST_USER = EMAIL_NOTIFICATION_USER

if EMAIL_NOTIFICATION_PWD and not EMAIL_HOST_PASSWORD:
    EMAIL_HOST_PASSWORD = EMAIL_NOTIFICATION_PWD


# ------------------------------------------------------------------------------
# Testing settings

SELENIUM_USE_CHROME = False  # Set to True to use Chrome instead of FF (requires ChromeDriver)
SELENIUM_CHROME_PATH = ''  # Set full path of Chromedriver binary if SELENIUM_USE_CHROME == True
SELENIUM_VIRTUAL_DISPLAY = False  # Set to True to use headless browser for testing (requires xvfb)

if any([('py.test' in v or 'pytest' in v) for v in sys.argv]):
    DATABASES.pop('readonly', None)
    from .test_settings import *  # noqa

if DEBUG_TOOLBAR:
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')


USE_ADFS = (
    'qatrack.accounts.backends.QATrackAdfsAuthCodeBackend' in AUTHENTICATION_BACKENDS or
    'django_adfs.backends.AdfsAuthCodeBackend' in AUTHENTICATION_BACKENDS
)

if USE_ADFS:
    INSTALLED_APPS.append('django_auth_adfs')


if USE_SQL_REPORTS:
    INSTALLED_APPS += [
        'explorer',
        'xlsxwriter',
    ]

    # use default database when testing
    if any(('py.test' in arg or 'pytest' in arg) for arg in sys.argv):
        EXPLORER_CONNECTIONS = {'Default': 'default'}
        EXPLORER_DEFAULT_CONNECTION = 'default'
    elif 'readonly' not in DATABASES:
        raise ValueError(
            "Missing 'readonly' connection information. Either set "
            "USE_SQL_REPORTS = False or set up readonly database connection"
        )

LOGOUT_REDIRECT_URL = LOGIN_URL

Q_CLUSTER = {
    'name': 'qatrack',
    'workers': 2,
    'timeout': 60,
    'catch_up': True,
    'recycle': 20,
    'compress': False,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'orm': 'default',
}
