# Set to True to enable debug mode (not safe for regular use!)
DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql', 'mysql', 'sqlite3'
        'NAME': 'qatrackplus',  # Or path to database file if using sqlite3.
        'USER': '',  # Not used with sqlite3.
        'PASSWORD': '',  # Not used with sqlite3.
        'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',  # Set to empty string for default. Not used with sqlite3.
    },
    'readonly': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql', 'mysql', 'sqlite3'
        'NAME': 'qatrackplus',  # Or path to database file if using sqlite3.
        'USER': '',  # Not used with sqlite3.
        'PASSWORD': '',  # Not used with sqlite3.
        'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',  # Set to empty string for default. Not used with sqlite3.
    }
}


# Change XX.XXX.XXX.XX to your servers IP address and/or host name e.g. ALLOWED_HOSTS = ['54.123.45.1', 'yourhostname']
ALLOWED_HOSTS = ['XX.XXX.XXX.XX']

# CSRF_TRUSTED_ORIGINS is required for Django 4.0+. It must include the scheme (http/https).
CSRF_TRUSTED_ORIGINS = ['http://XX.XXX.XXX.XX', 'https://XX.XXX.XXX.XX']

# Set to False to disable the SQL Query Tool
USE_SQL_REPORTS =  True

# If you host your QATrack+ instance at a non root url (e.g. 12.345.678.9/qatrack)
# then you need to uncomment (and possibly modify) the following settings
# FORCE_SCRIPT_NAME = "/qatrack"
# LOGIN_EXEMPT_URLS = [r"^qatrack/accounts/", r"qatrack/api/*"]
# LOGIN_REDIRECT_URL = '/qatrack/qa/unit/'
# LOGIN_URL = "/qatrack/accounts/login/"


# Who to email when server errors occur
ADMINS = (
    ('Admin Name', 'YOUR_EMAIL_ADDRESS_GOES_HERE'),
)
MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Toronto'


# Precision to use when displaying constant values
CONSTANT_PRECISION = 8


# This is the warning message given to the user when a test result is out of tolerance
# Override this setting in local_settings.py to a locally relevant warning message
DEFAULT_WARNING_MESSAGE = "Do not treat"


# Display ordering on the "Choose Unit" page. (Use "name" or "number")
ORDER_UNITS_BY = "number"

# Enable or disable the "Difference" column when reviewing test lists
REVIEW_DIFF_COL = False

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


# Email and notification settings
EMAIL_NOTIFICATION_USER = None
EMAIL_NOTIFICATION_PWD = None
EMAIL_NOTIFICATION_TEMPLATE = "notification_email.html"
EMAIL_NOTIFICATION_SENDER = "qatrack@yourmailhost.com"
# use either a static subject or a customizable template
# EMAIL_NOTIFICATION_SUBJECT = "QATrack+ Test Status Notification"
EMAIL_NOTIFICATION_SUBJECT_TEMPLATE = "notification_email_subject.txt"

EMAIL_FAIL_SILENTLY = True
EMAIL_HOST = ""  # e.g. 'smtp.gmail.com'
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
