# Test-specific settings for QATrack+ - MySQL variant
#
# Copy to qatrack/local_test_settings.mysql.py and run
# `poe test-engine mysql`, or to qatrack/local_test_settings.py to make it
# your everyday choice.
#
# The connection details come from the environment, with defaults matching
# deploy/dev/compose.test-databases.yaml - so `poe test-databases-up` and this
# file agree without either being edited. Point them somewhere else by
# exporting the variables, or by editing deploy/dev/.env.
#
# Reading the port from the same variable the compose file publishes is
# deliberate: a hardcoded port here and a different one in the container is a
# failure whose only symptom is a port that never comes up.

import os

DEBUG = True
TEMPLATE_DBG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'qatrackplus_test',
        # root, because the suite creates and drops test_<NAME> and a user
        # scoped to one database cannot do that.
        'USER': os.environ.get('QATRACK_TEST_MYSQL_USER', 'root'),
        'PASSWORD': os.environ.get('QATRACK_TEST_MYSQL_PASSWORD', 'qatrack-test-only'),
        'HOST': os.environ.get('QATRACK_TEST_MYSQL_HOST', '127.0.0.1'),
        'PORT': os.environ.get('QATRACK_TEST_MYSQL_PORT', '3306'),
    }
}
DATABASES['readonly'] = DATABASES['default']

# Everything below is unchanged from the other templates in this directory.

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
