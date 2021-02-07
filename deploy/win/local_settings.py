# Set to True to enable debug mode (not safe for regular use!)
DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'sql_server.pyodbc',
        'NAME': 'qatrackplus031',
        'USER': '',  # USER/PWD can usually be left blank if SQL server is running on the same server as QATrack+
        'PASSWORD': '',
        'HOST':
            '',  # leave blank unless using remote server or SQLExpress (use 127.0.0.1\\SQLExpress or COMPUTERNAME\\SQLExpress)
        'PORT': '',  # Set to empty string for default. Not used with sqlite3.
    },
    'default': {
        'ENGINE': 'sql_server.pyodbc',
        'NAME': 'qatrackplus031',
        'USER': 'qatrack_reports',
        'PASSWORD': 'qatrackpass',
        'HOST': '',  # leave blank unless using remote server or SQLExpress (use 127.0.0.1\\SQLExpress or COMPUTERNAME\\SQLExpress)
        'PORT': '',  # Set to empty string for default. Not used with sqlite3.
    }
}

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# needs to be set to True when running behind reverse proxy (normal deploy)
# set to False when not running behind reverse proxy
# Use True for e.g. CherryPy/IIS and False for Apache/mod_wsgi
USE_X_FORWARDED_HOST = True

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
