# Localization settings. 
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# If running in a Windows environment this must be set to the same as your system time zone.

TIME_ZONE = 'America/Toronto'
LANGUAGES = [('en', 'English'), ('fr', 'Français'), ('es', 'Español')]
LANGUAGE_CODE = 'en'


DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'qatrack',
        'USER': 'qatrack',
        'PASSWORD': 'qatrackpass',
        'HOST': '',  # leave blank unless using remote server or SQLExpress (use 127.0.0.1\\SQLExpress or COMPUTERNAME\\SQLExpress)
        'PORT': '',  # Set to empty string for default. Not used with sqlite3.
        'OPTIONS': {'driver': 'ODBC Driver 17 for SQL Server'},
    },
    'readonly': {
        'ENGINE': 'mssql',
        'NAME': 'qatrack',
        'USER': 'qatrack_reports',
        'PASSWORD': 'qatrackpass',
        'HOST': '',  # leave blank unless using remote server or SQLExpress (use 127.0.0.1\\SQLExpress or COMPUTERNAME\\SQLExpress)
        'PORT': '',  # Set to empty string for default. Not used with sqlite3.
        'OPTIONS': {'driver': 'ODBC Driver 17 for SQL Server'},
    },
}


ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'YOUR_HOST_NAME_HERE']  # Windows key + i -> System -> About -> Device Name
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1',
    'https://127.0.0.1',
    'http://localhost',
    'https://localhost',
    'http://YOUR_HOST_NAME_HERE',
    'https://YOUR_HOST_NAME_HERE',
]

# Who to email when server errors occur
ADMINS = (('Admin Name', 'YOUR_EMAIL_ADDRESS_GOES_HERE'),)
MANAGERS = ADMINS

# Set to True to enable debug mode (not safe for regular use!)
DEBUG = False

# needs to be set to True when running behind reverse proxy (normal deploy)
# set to False when not running behind reverse proxy
# Use True for e.g. CherryPy/IIS and False for Apache/mod_wsgi
USE_X_FORWARDED_HOST = True
# -----------------------------------------------------------------------------
# Backup settings
# Use the python manage.py backup_site command to backup the database and uploads
# BACKUP_DIR = "C:\\deploy\\backups"
# BACKUP_WEEKLY_DAY = 2  # 0 = Monday, 6 = Sunday (2 = Wednesday)
# BACKUP_MONTHLY_DAY = 3
# BACKUP_DAYS_TO_KEEP = 7
# BACKUP_WEEKS_TO_KEEP = 5
# BACKUP_MONTHS_TO_KEEP = 12


# If you host your QATrack+ instance at a non root url (e.g. 12.345.678.9/qatrack)
# then you need to uncomment (and possibly modify) the following settings
# FORCE_SCRIPT_NAME = "/qatrack"
# LOGIN_EXEMPT_URLS = [r"^qatrack/accounts/", r"qatrack/api/*"]
# LOGIN_REDIRECT_URL = '/qatrack/qa/unit/'
# LOGIN_URL = "/qatrack/accounts/login/"


# Precision to use when displaying constant values
CONSTANT_PRECISION = 8


# This is the warning message given to the user when a test result is out of tolerance
# Override this setting in local_settings.py to a locally relevant warning message
DEFAULT_WARNING_MESSAGE = 'Do not treat'


# Display ordering on the "Choose Unit" page. (Use "name" or "number")
ORDER_UNITS_BY = 'number'

# Enable or disable the "Difference" column when reviewing test lists
REVIEW_DIFF_COL = False

# default display settings for test statuses
TEST_STATUS_DISPLAY = {
    'fail': 'Fail',
    'not_done': 'Not Done',
    'done': 'Done',
    'ok': 'OK',
    'tolerance': 'Tolerance',
    'action': 'Action',
    'no_tol': 'No Tol Set',
}

# default short display settings for test statuses
TEST_STATUS_DISPLAY_SHORT = {
    'fail': 'Fail',
    'not_done': 'Not Done',
    'done': 'Done',
    'ok': 'OK',
    'tolerance': 'TOL',
    'action': 'ACT',
    'no_tol': 'NO TOL',
}


# Email and notification settings
EMAIL_NOTIFICATION_USER = None
EMAIL_NOTIFICATION_PWD = None
EMAIL_NOTIFICATION_TEMPLATE = 'notification_email.html'
EMAIL_NOTIFICATION_SENDER = 'qatrack@yourmailhost.com'
# use either a static subject or a customizable template
# EMAIL_NOTIFICATION_SUBJECT = "QATrack+ Test Status Notification"
EMAIL_NOTIFICATION_SUBJECT_TEMPLATE = 'notification_email_subject.txt'

EMAIL_FAIL_SILENTLY = True
EMAIL_HOST = ''  # e.g. 'smtp.gmail.com'
EMAIL_HOST_USER = ''  # e.g. "randle.taylor@gmail.com"
EMAIL_HOST_PASSWORD = 'your_password_here'
EMAIL_USE_TLS = True
EMAIL_PORT = 587


# ------------------------------------------------------------------------------
# Dates and times
#
# By default QATrack+ shows dates as YYYY-MM-DD HH:MM, in every language, and
# the date pickers write that same format into the field. ISO order is the
# default because it sorts correctly and cannot be misread - 03/04 is the 3rd
# of April to half the world and the 4th of March to the other half.
#
# To change it, set the format you want here. Everything follows from it: what
# is displayed, what the date pickers produce, and the help text under each
# date field. Use Python strptime syntax (%Y year, %m month, %d day, %H hour,
# %M minute).
#
# QATRACK_DATETIME_FORMAT = "%Y/%m/%d %H:%M"   # 2012/05/31 14:30
# QATRACK_DATE_FORMAT = "%Y/%m/%d"             # 2012/05/31
# QATRACK_TIME_FORMAT = "%H:%M"
#
# ...or with a month name, also unambiguous:
#
# QATRACK_DATETIME_FORMAT = "%d %b %Y %H:%M"   # 31 May 2012 14:30
# QATRACK_DATE_FORMAT = "%d %b %Y"             # 31 May 2012
#
# Typing a date is separate from displaying one. QATrack+ always accepts the
# format above, plus the ones listed below. Adding to this list lets people
# enter dates whichever way they are used to without changing what anybody
# sees - it only affects what is understood on the way in.
#
# QATRACK_EXTRA_DATETIME_INPUT_FORMATS = [
#     "%d %b %Y %H:%M",     # 31 May 2012 14:30
#     "%d/%m/%Y %H:%M",     # 31/05/2012 14:30
# ]
# QATRACK_EXTRA_DATE_INPUT_FORMATS = [
#     "%Y/%m/%d",           # 2012/05/31
#     "%d %b %Y",           # 31 May 2012
# ]
#
# On DD/MM/YYYY and MM/DD/YYYY: deliberately not suggested here.
#
# 03/05/2026 is the 3rd of May to most of the world and March 5th in the
# United States. Nothing in the string says which, and because the US
# convention is entrenched, both readings turn up in the same datasets. In
# most software that is an annoyance. In a QC record it is the date a machine
# was or was not verified - read later by colleagues trained in a different
# convention, and by people who were not there. Medical physics writes dates
# unambiguously for that reason, and QATrack+ follows suit rather than making
# it your problem.
#
# So the defaults are ISO, and YYYY/MM/DD and month-name formats are the
# alternatives offered: none of them can be read two ways. Neither numeric
# day/month order is blocked - it is your deployment - but configuring one
# raises a warning at startup (qatrack.W004), and configuring *both* raises a
# stronger one, because at that point the same text typed by two people means
# two different days.
#
# Note the JSON API is deliberately unaffected by all of this - its date
# format is fixed so that changing your display preference cannot break an
# integration that parses it.
