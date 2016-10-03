
import os

from selenium import webdriver
from .settings import PROJECT_ROOT, INSTALLED_APPS

INSTALLED_APPS += (
    'django_nose',
)

COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'locale$',
    'common.views.test', '__init__', 'django', 'migrations'
]

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
TEST_DISCOVER_TOP_LEVEL = PROJECT_ROOT
TEST_DISCOVER_ROOT = PROJECT_ROOT
TEST_DISCOVER_PATTERN = "test_*.py"
NOSE_ARGS = [
    '--with-coverage',  # activate coverage report
    # '--with-doctest',  # activate doctest: find and run docstests
    '--verbosity=1',  # verbose output
    # '--with-xunit',  # enable XUnit plugin
    # '--xunit-file=xunittest.xml',  # the XUnit report file
    '--cover-xml',  # produle XML coverage info
    '--cover-xml-file=coverage.xml',  # the coverage info file
    '--cover-package=qatrack.qa,qatrack.units,qatrack.contacts,qatrack.accounts',
    '--nocapture',
    '--nologcapture',
    '--with-id',
]
# IN-MEMORY TEST DATABASE
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    },
}

NOTIFICATIONS_ON = False
DEBUG = True

SELENIUM_DRIVER = webdriver.Firefox
os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = 'localhost:8000'
