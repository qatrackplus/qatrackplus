# Test-specific settings for QATrack+ - MySQL variant
# Copy this file to qatrack/local_test_settings.py and customize as needed
#
# Requires the `mysql` extra: uv sync --extra mysql

DEBUG = True
TEMPLATE_DBG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'qatrackplus_test',
        'USER': 'your_mysql_user',
        'PASSWORD': 'your_mysql_password',
        'HOST': 'hostname',
        'PORT': '3306',  # MySQL default
    }
}
DATABASES['readonly'] = DATABASES['default']

# Test-specific settings
NOTIFICATIONS_ON = False
DEFAULT_NUMBER_FORMAT = None
AD_CLEAN_USERNAME = None
HTTP_OR_HTTPS = "http"
REVIEW_BULK = True
TIME_ZONE = 'America/Toronto'

# Selenium: which browser, and whether it is visible. Either can come from
# the environment for a one-off run instead:
#   SELENIUM_BROWSER=chromium pytest --run-selenium           # bash/zsh
#   $env:SELENIUM_BROWSER='chromium'; pytest --run-selenium   # PowerShell
# Selenium Manager resolves the driver itself; settings.py has the variables
# for pinning a specific binary.
#
# SELENIUM_BROWSER = 'chromium'   # 'firefox' is the default
# SELENIUM_HEADLESS = False       # watch it run; needs a real display

AUTHENTICATION_BACKENDS = ['qatrack.accounts.backends.QATrackAccountBackend']

# Customize any of the above settings as needed for your test environment
