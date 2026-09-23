""" settings.py

    Default settings for QATrack+

    isort:skip_file
"""

import datetime
import json
import os
import pathlib
import sys

import matplotlib
from django.utils.translation import gettext_lazy as _l

matplotlib.use("Agg")

# -----------------------------------------------------------------------------
DEBUG = False
DEBUG_TOOLBAR = False

# Who to email when server errors occur
ADMINS = (('Admin Name', 'YOUR_EMAIL_ADDRESS_GOES_HERE'),)

SEND_BROKEN_LINK_EMAILS = False

# -----------------------------------------------------------------------------
# misc settings
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

LOG_ROOT = os.path.join(PROJECT_ROOT, "..", "logs")
LOCALE_PATHS = [
    os.path.join(PROJECT_ROOT, 'locale'),
]
VERSION = "4.0.0"
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
# please do so in local_settings.py 
DATABASES = {
}

# -----------------------------------------------------------------------------
# Backup settings
# Override these in local_settings.py if you are using the backup_site command.
BACKUP_DIR = "C:\\deploy\\backups"
BACKUP_WEEKLY_DAY = 2  # 0 = Monday, 6 = Sunday (2 = Wednesday)
BACKUP_MONTHLY_DAY = 3

BACKUP_DAYS_TO_KEEP = 7
BACKUP_WEEKS_TO_KEEP = 5
BACKUP_MONTHS_TO_KEEP = 12

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
LANGUAGE_CODE = 'en'
# Duration of the language cookie 
# TODO: add nice documentation to the local_settings defaults so deployment is clear. 
LANGUAGE_COOKIE_AGE = 360 * 24 * 60 * 60  # 1 year

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
# USE_L10N = True # deprecated in Django 4.0+, always on now
LANGUAGES = [('en', 'English'), ('fr', 'Français'), ('fr-ca', 'Français (Canada)'), ('es', 'Español')]
CONSTANT_PRECISION = 8
DEFAULT_NUMBER_FORMAT = None
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# This is the warning message given to the user when a test result is out of tolerance
# Override this setting in local_settings.py to a locally relevant warning message
DEFAULT_WARNING_MESSAGE = _l("Do not treat")

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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.RemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'qatrack.middleware.login_required.LoginRequiredMiddleware',
    'qatrack.middleware.maintain_filters.FilterPersistMiddleware',
]

# login required middleware settings
LOGIN_EXEMPT_URLS = [r"^favicon.ico$", r"^accounts/", r"api/*", r"^oauth2/*", r"^i18n/"]
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
            'debug':
                False,
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
                'qatrack.context_processors.available_languages',
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
    'django.contrib.admin', 'django.contrib.contenttypes', 'django.contrib.auth', 'django.contrib.sessions',
    'django.contrib.sites', 'django.contrib.messages', 'django.contrib.staticfiles', 'django.contrib.humanize',
    'django_extensions', 'django_q', 'django_comments', 'formtools', 'django_filters', 'rest_framework',
    'rest_framework_filters', 'rest_framework.authtoken', 'listable', 'qatrack.genericdropdown', 'recurrence',
    'widget_tweaks', 'dynamic_raw_id', 'mptt', 'django_mptt_admin', 'qatrack.cache', 'qatrack.accounts',
    'qatrack.units', 'qatrack.qa', 'qatrack.qatrack_core', 'qatrack.notifications', 'qatrack.contacts',
    'qatrack.issue_tracker', 'qatrack.service_log', 'qatrack.parts', 'qatrack.faults', 'qatrack.attachments',
    'qatrack.reports', 'qatrack.form_utils'
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

# Active Directory settings (not required if only using QATrackAccountBackend)
AD_DNS_NAME = ''  # e.g. ad.civic1.ottawahospital.on.ca

# If using non-SSL use these
AD_LDAP_PORT = 389
AD_LDAP_PROTOCOL = "ldap"

# If using SSL use these:
# AD_LDAP_PORT = 636
# AD_LDAP_PROTOCOL = "ldaps"

AD_LDAP_USER = ''  # only used for WindowsIntegratedAuthenticationBackend
AD_LDAP_PW = ''  # only used for WindowsIntegratedAuthenticationBackend

AD_LU_ACCOUNT_NAME = "sAMAccountName"
AD_LU_MAIL = "mail"
AD_LU_SURNAME = "sn"
AD_LU_GIVEN_NAME = "givenName"
AD_LU_MEMBER_OF = "memberOf"

AD_SEARCH_DN = ""  # eg "dc=ottawahospital,dc=on,dc=ca"
AD_NT4_DOMAIN = ""  # Network domain that AD server is part of

AD_SEARCH_FIELDS = [AD_LU_MAIL, AD_LU_SURNAME, AD_LU_GIVEN_NAME, AD_LU_ACCOUNT_NAME, AD_LU_MEMBER_OF]

# If AD_MIRROR_GROUPS is True then a QATrack+ group will be created with the
# same name as the AD group if it doesn't exist.
AD_MIRROR_GROUPS = False

AD_CERT_FILE = ''  # AD_CERT_FILE = '/path/to/your/cert.txt'

CLEAN_USERNAME_STRING = AD_CLEAN_USERNAME_STRING = ''

# Define a function called AD_CLEAN_USERNAME in local_settings.py if you
# wish to clean usernames before sending to ldap server.
AD_CLEAN_USERNAME = None

# For docker deployment, since we can't define a python function for AD_CLEAN_USERNAME,
# choose one of the predefined cleaning options using the AD_USERNAME_CLEANING setting:
#   "none"              : no cleaning, just use the username as-is
#   "lower"             : user username in lower-case characters
#   "strip_domain"      : strip the domain, keep username after "\\"
#   "strip_upn"         : keep username before "@"
#   "lower_strip_domain": combines lower and strip_domain
#   "lower_strip_upn"   : combines lower and strip_upn

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
    if not record.args or not isinstance(record.args[0], str):
        return True
    skip = (record.args[0].startswith("GET /static/") or record.args[0].startswith("GET /accounts/ping/"))
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
        'django-q2': {
            'level': 'INFO',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOG_ROOT, "django-q2.log"),
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
        'django-q2': {
            'handlers': ['console', 'django-q2'],
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
    'fail': _l("Fail"),
    'not_done': _l("Not Done"),
    'done': _l("Done"),
    'ok': _l("OK"),
    'tolerance': _l("Tolerance"),
    'action': _l("Action"),
    'no_tol': _l("No Tol Set"),
}

# default short display settings for test statuses
TEST_STATUS_DISPLAY_SHORT = {
    'fail': _l("Fail"),
    'not_done': _l("Not Done"),
    'done': _l("Done"),
    'ok': _l("OK"),
    'tolerance': _l("TOL"),
    'action': _l("ACT"),
    'no_tol': _l("NO TOL"),
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

DELETE_REASONS = ((_l('Duplicate'), _l('Duplicate')), (_l('Invalid'), _l('Invalid')))

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
EXPLORER_SQL_BLACKLIST = [
    'ALTER', 'RENAME ', 'DROP', 'TRUNCATE', 'INSERT INTO', 'UPDATE', 'REPLACE', 'DELETE', 'CREATE TABLE',
    'SCHEMA', 'GRANT', 'OWNER TO'
]  # noqa: E501


def EXPLORER_PERMISSION_CHANGE(request):
    return request.user.has_perm("reports.can_create_sql_reports")


def EXPLORER_PERMISSION_VIEW(request):
    return request.user.has_perm("reports.can_run_sql_reports")


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


def env_bool(value):
    """Converts an env value to bool."""
    normalized = value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"Invalid Boolean environment value: '{value}'")


def env_json(value):
    """Loads an env variable JSON value."""
    return json.loads(value)


def env_csv(value, value_type=str):
    """Converts a comma-separated list of values to a list."""
    return [value_type(_.strip()) for _ in value.split(",") if _.strip()]


def required_env(name):
    """
    Checks that a required env variable is provided  and non-empty.
    If so, returns the value.
    
    Strips whitespace.
    """
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Required environment variable is missing, or has empty value: {name}")
    return value.strip()


def override_from_env(setting_name, converter=str):
    """
    Override or set a Django setting from an env variable.
    
    Strips whitespace.
    """
    if setting_name not in os.environ:
        return

    value = os.environ[setting_name].strip()

    try:
        converted = converter(value)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Invalid value for environment setting {setting_name}"
        ) from exc

    globals()[setting_name] = converted
    return converted


# ------------------------------------------------------------------------------
# local_settings contains anything that should be overridden
# based on site specific requirements (e.g. deployment, development etc)
#
# If USE_DOCKER is set, all local settings are taken from env variables.
# If not, the local_settings module is imported.
use_docker = env_bool(os.getenv('USE_DOCKER', '0'))
if use_docker:
    ALLOWED_HOSTS = env_csv(required_env("ALLOWED_HOSTS"))

    secret_filepath = pathlib.Path(PROJECT_ROOT, "secrets", "secret_key.txt")

    # Allow SECRET_KEY to be specified with env var
    secret_key_from_env = os.getenv("SECRET_KEY")
    if secret_key_from_env:
        SECRET_KEY = secret_key_from_env.strip()
    else:
        # If not specified in env var, try to read it from secret_key.txt
        try:
            with open(secret_filepath, encoding="utf-8") as f:
                SECRET_KEY = f.read().strip()

            if not SECRET_KEY:
                raise ValueError(
                    f"Secret key file is empty: {secret_filepath}"
                )
        except FileNotFoundError:
            # Fall back to generating it automatically.
            # It will be persisted in the user-data-volume.
            import secrets
            secret_filepath.parent.mkdir(parents=True, exist_ok=True)
            SECRET_KEY = secrets.token_urlsafe(64)
            with open(secret_filepath, 'w', encoding="utf-8") as f:
                f.write(SECRET_KEY)
            secret_filepath.chmod(0o600)

    # Database settings
    POSTGRES_DB = required_env("POSTGRES_DB")
    POSTGRES_USER = required_env("POSTGRES_USER")
    POSTGRES_PASSWORD = required_env("POSTGRES_PASSWORD")

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': POSTGRES_DB,
            'USER': POSTGRES_USER,
            'PASSWORD': POSTGRES_PASSWORD,
            'HOST': os.getenv("POSTGRES_HOST", "postgres"),
            'PORT': int(os.getenv("POSTGRES_PORT", "5432"))
        }
    }

    override_from_env("USE_SQL_REPORTS", converter=env_bool)
    if 'readonly' not in DATABASES and USE_SQL_REPORTS:
        DATABASES['readonly'] = DATABASES['default']

    # General Django settings
    override_from_env("ADMINS", converter=env_json)  # JSON format: [["Admin Name", "admin@example.com"]]
    override_from_env("SEND_BROKEN_LINK_EMAILS", converter=env_bool)
    override_from_env("SITE_NAME")
    override_from_env("TIME_ZONE")
    override_from_env("USE_TZ", converter=env_bool)
    override_from_env("USE_I18N", converter=env_bool)
    override_from_env("LANGUAGE_CODE")

    # Hard-coded roots to conform with Dockerfile and conpose file
    MEDIA_ROOT = "/app_data/media"
    STATIC_ROOT = "/app_data/static"

    # QATrack settings
    override_from_env("DEFAULT_WARNING_MESSAGE")
    override_from_env("ICON_SETTINGS", converter=env_json)  # JSON format: {"SHOW_DUE_ICONS": true, ...}
    override_from_env("NHIST", converter=int)
    override_from_env("PING_INTERVAL_S", converter=int)
    override_from_env("CATEGORY_FIRST_OF_GROUP_ONLY", converter=env_bool)
    override_from_env("CHOOSE_UNIT_CATEGORY_DROPDOWN", converter=env_bool)
    override_from_env("ORDER_UNITS_BY")
    override_from_env("REVIEW_DIFF_COL", converter=env_bool)
    override_from_env("REVIEW_BULK", converter=env_bool)
    override_from_env("TEST_STATUS_DISPLAY", converter=env_json)  # JSON format: {"no_tol": "No Tol Set", ...}
    override_from_env("TEST_STATUS_DISPLAY_SHORT", converter=env_json)  # JSON format: {"no_tol": "NO TOL", ...}
    DEFAULT_AVAILABLE_TIMES = {
        'hours_sunday': datetime.timedelta(hours=int(os.getenv("DEFAULT_AVAILABLE_HOURS_SUNDAY") or 0), minutes=0),
        'hours_monday': datetime.timedelta(hours=int(os.getenv("DEFAULT_AVAILABLE_HOURS_MONDAY") or 8), minutes=0),
        'hours_tuesday': datetime.timedelta(hours=int(os.getenv("DEFAULT_AVAILABLE_HOURS_TUESDAY") or 8), minutes=0),
        'hours_wednesday': datetime.timedelta(hours=int(os.getenv("DEFAULT_AVAILABLE_HOURS_WEDNESDAY") or 8), minutes=0),
        'hours_thursday': datetime.timedelta(hours=int(os.getenv("DEFAULT_AVAILABLE_HOURS_THURSDAY") or 8), minutes=0),
        'hours_friday': datetime.timedelta(hours=int(os.getenv("DEFAULT_AVAILABLE_HOURS_FRIDAY") or 8), minutes=0),
        'hours_saturday': datetime.timedelta(hours=int(os.getenv("DEFAULT_AVAILABLE_HOURS_SATURDAY") or 0), minutes=0),
    }

    # Session settings
    override_from_env("SESSION_COOKIE_AGE", converter=int)
    override_from_env("SESSION_SAVE_EVERY_REQUEST", converter=env_bool)
    override_from_env("SESSION_EXPIRE_AT_BROWSER_CLOSE", converter=env_bool)

    override_from_env("CSRF_COOKIE_NAME")

    override_from_env("USE_X_FORWARDED_HOST", converter=env_bool)  # Already at False by default

    override_from_env("HTTP_OR_HTTPS")  # QATrack setting. Must be 'http' or 'https'
    if HTTP_OR_HTTPS not in ("http", "https"):
        raise ValueError("HTTP_OR_HTTPS must be either 'http' or 'https'")

    SECURE_PROXY_SSL_HEADER = None
    if HTTP_OR_HTTPS == "https":
        SECURE_PROXY_SSL_HEADER = (
            "HTTP_X_FORWARDED_PROTO",
            "https",
        )
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
    else:
        SESSION_COOKIE_SECURE = False
        CSRF_COOKIE_SECURE = False

    CSRF_TRUSTED_ORIGINS = override_from_env("CSRF_TRUSTED_ORIGINS", converter=env_csv)
    if not CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS = [
            scheme + host
            for host in ALLOWED_HOSTS
            for scheme in ('http://', 'https://')  # TODO: limit this to protocol set in HTTP_OR_HTTPS?
            if host != '*'
        ]

    override_from_env("SESSION_COOKIE_SECURE", converter=env_bool)
    override_from_env("CSRF_COOKIE_SECURE", converter=env_bool)

    # Email settings
    override_from_env("EMAIL_NOTIFICATION_TEMPLATE")
    override_from_env("EMAIL_NOTIFICATION_SUBJECT")
    override_from_env("EMAIL_NOTIFICATION_SUBJECT_TEMPLATE")
    override_from_env("EMAIL_NOTIFICATION_SENDER")
    override_from_env("EMAIL_FAIL_SILENTLY", converter=env_bool)
    override_from_env("EMAIL_HOST")
    override_from_env("EMAIL_HOST_USER")
    override_from_env("EMAIL_HOST_PASSWORD")
    override_from_env("EMAIL_USE_TLS", converter=env_bool)
    override_from_env("EMAIL_PORT", converter=int)

    # Debug settings
    override_from_env("DEBUG", converter=env_bool)
    override_from_env("DEBUG_TOOLBAR", converter=env_bool)

    # Auth
    override_from_env("AUTHENTICATION_BACKENDS", converter=env_csv)

    override_from_env("ACCOUNTS_SELF_REGISTER", converter=env_bool)
    override_from_env("ACCOUNTS_PASSWORD_RESET", converter=env_bool)
    override_from_env("ACCOUNT_ACTIVATION_DAYS", converter=int)

    override_from_env("AD_DNS_NAME")
    override_from_env("AD_LDAP_PROTOCOL")
    override_from_env("AD_LDAP_PORT", converter=int)

    override_from_env("AD_LDAP_USER")
    override_from_env("AD_LDAP_PW")
    override_from_env("AD_MIRROR_GROUPS", converter=env_bool)

    override_from_env("AD_LU_ACCOUNT_NAME")
    override_from_env("AD_LU_MAIL")
    override_from_env("AD_LU_SURNAME")
    override_from_env("AD_LU_GIVEN_NAME")
    override_from_env("AD_LU_MEMBER_OF")

    # Regenerate AD_SEARCH_FIELDS from values overriden above
    AD_SEARCH_FIELDS = [
        AD_LU_MAIL,
        AD_LU_SURNAME,
        AD_LU_GIVEN_NAME,
        AD_LU_ACCOUNT_NAME,
        AD_LU_MEMBER_OF,
    ]
    # Or, if user specifies directly AD_SEARCH_FIELDS, weoverride its value below
    override_from_env("AD_SEARCH_FIELDS", converter=env_csv)

    override_from_env("AD_SEARCH_DN")
    override_from_env("AD_NT4_DOMAIN")

    override_from_env("AD_CERT_FILE")

    override_from_env("CLEAN_USERNAME_STRING")
    override_from_env("AD_CLEAN_USERNAME_STRING")

    ad_username_cleaning = os.getenv("AD_USERNAME_CLEANING")

    def clean_username(username):
        """
        For docker deployment, since we won't pass in python functions
        with env vars, we define a set of common username cleaning options.
        """
        if ad_username_cleaning is None or not ad_username_cleaning:
            return username

        strategy = ad_username_cleaning.strip().lower()

        if strategy == "none":
            return username

        if strategy == "lower":
            return username.lower()

        if strategy == "strip_domain":
            return username.split("\\")[-1]

        if strategy == "lower_strip_domain":
            return username.lower().split("\\")[-1]

        if strategy == "strip_upn":
            return username.split("@")[0]

        if strategy == "lower_strip_upn":
            return username.lower().split("@")[0]

        raise ValueError(
            f"Unknown AD_USERNAME_CLEANING strategy: {strategy}"
        )

    AD_CLEAN_USERNAME = clean_username

    override_from_env("AUTH_ADFS", converter=env_json)  # JSON format: {"SERVER": "some.adfs.server.com", ...}

    # For advanced users who want to customize settings of the REST API
    # You can specify keys of REST_FRAMEWORK which will then be merged with the
    # default configuration.
    REST_FRAMEWORK_DEFAULTS = REST_FRAMEWORK.copy()
    REST_FRAMEWORK_OVERRIDE = override_from_env("REST_FRAMEWORK", converter=env_json) or {}
    REST_FRAMEWORK = REST_FRAMEWORK_DEFAULTS | REST_FRAMEWORK_OVERRIDE
else:
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

# region: pathlib recreation of path checks and creation.  
# This is to avoid issues with os.path.exists() returning False for symlinks to directories
# os.path variables are left in place for backwards compatibility with other code that may use them
MEDIA_ROOT_PATH = pathlib.Path(MEDIA_ROOT)
UPLOAD_ROOT_PATH = pathlib.Path(UPLOAD_ROOT)
TMP_UPLOAD_ROOT_PATH = pathlib.Path(TMP_UPLOAD_ROOT)
TMP_REPORT_ROOT_PATH = pathlib.Path(TMP_REPORT_ROOT)
LOG_ROOT_PATH = pathlib.Path(LOG_ROOT)

for d in (MEDIA_ROOT_PATH, UPLOAD_ROOT_PATH, TMP_UPLOAD_ROOT_PATH, LOG_ROOT_PATH, TMP_REPORT_ROOT_PATH):
    if not d.exists() and not d.is_dir():
        d.mkdir(parents=True, exist_ok=True)
# endregion


CACHE_LOCATION = os.path.join(PROJECT_ROOT, "cache", "cache_data")
IS_FILE_CACHE = CACHES['default']['BACKEND'] == 'django.core.cache.backends.filebased.FileBasedCache'
if IS_FILE_CACHE and not os.path.isdir(CACHE_LOCATION):
    pathlib.Path(CACHE_LOCATION).mkdir(parents=True, exist_ok=True)

if FORCE_SCRIPT_NAME:
    # Django admin URLs are handled automatically through standard URL routing
    pass

# no longer using EMAIL_NOTIFICATION_USER/PWD but people may have
# notification specific settings set.
if EMAIL_NOTIFICATION_USER and not EMAIL_HOST_USER:
    EMAIL_HOST_USER = EMAIL_NOTIFICATION_USER

if EMAIL_NOTIFICATION_PWD and not EMAIL_HOST_PASSWORD:
    EMAIL_HOST_PASSWORD = EMAIL_NOTIFICATION_PWD

# ------------------------------------------------------------------------------
# Testing settings

# Selenium Browser Configuration
# Options: 'firefox', 'chromium'
# Set to 'firefox' to use Firefox, 'chromium' to use Chromium
SELENIUM_BROWSER = ''

# Browser Driver Paths (leave empty to use system default)
SELENIUM_FIREFOX_DRIVER_PATH = ''  # Path to geckodriver
SELENIUM_CHROMIUM_DRIVER_PATH = ''   # Path to chromedriver

# Headless Mode
# Set to True to run browsers in headless mode (no visible browser window)
# Set to False to see the browser during test execution
SELENIUM_VIRTUAL_DISPLAY = False  # Set to True to use headless browser for testing (requires xvfb)

if any(('py.test' in v or 'pytest' in v) for v in sys.argv):
    DATABASES.pop('readonly', None)
    from .test_settings import *  # noqa

if DEBUG_TOOLBAR:
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

# Set MANAGERS after ADMINS has taken on its final value (after local_settings
# is imported or the use_docker branch is executed).
MANAGERS = ADMINS

# LDAP URL is composed from previously-defined settings.
# Set it here, after local_settings is imported or the use_docker branch
# has been executed if USE_DOCKER is set.
if AD_LDAP_PROTOCOL not in ("ldap", "ldaps"):
    raise ValueError(
        f"Invalid LDAP protocol: {AD_LDAP_PROTOCOL}, must be one of 'ldap', 'ldaps'"
    )
AD_LDAP_URL = '%s://%s:%s' % (AD_LDAP_PROTOCOL, AD_DNS_NAME, AD_LDAP_PORT)

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
