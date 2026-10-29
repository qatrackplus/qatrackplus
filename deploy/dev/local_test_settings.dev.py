# Test-specific settings for QATrack+
# Copy this file to qatrack/local_test_settings.py and customize as needed

# Development settings
DEBUG = True
TEMPLATE_DBG = True

# SQLite example
#
# TEST['NAME'] is set explicitly, and should always be set explicitly.
#
# Django does not use NAME for the test database on SQLite. It uses
# TEST['NAME'], and when that is unset it silently substitutes an in-memory
# database - `TEST["NAME"] or ":memory:"` in
# django/db/backends/sqlite3/creation.py::_get_test_db_name. So a SQLite test
# run does not touch NAME at all, and a file named here is not the file the
# tests use. Spelling TEST['NAME'] out means the test database is stated rather
# than inferred.
#
# What the silence hides matters: when TEST['NAME'] *is* a real file,
# _create_test_db() erases that file before the run. A test database must
# therefore always have 'test' in its name, and must never be the development
# database.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db/default.db',
        'TEST': {'NAME': ':memory:'},
    }
}

# To keep the test database on disk so it can be inspected after a run, give
# TEST['NAME'] a test-named file instead:
#
#     'TEST': {'NAME': 'db/test_default.db'},
#
# Never point it at db/default.db: that is the development database, and the
# test runner would delete it.
#
# Naming the file is not enough on its own, and this is the part that surprises
# people: Django destroys the test database when the run finishes, so the file
# named above is created, used and deleted, leaving nothing to inspect. Ask for
# it to be kept:
#
#     pytest --reuse-db          # pytest-django, which is what this project uses
#     python manage.py test --keepdb
#
# `--reuse-db` also skips rebuilding the schema on the next run, which is most of
# why it is worth doing - and the reason to remember `--create-db` after a
# migration, model or fixture change, or the next run will be against yesterday's
# schema.

# SQL Server example
"""
DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'USER': 'testuser',
        'PASSWORD': '123456abc*$',
        'HOST': 'hostname',
        'PORT': '1433', # SQL Server default
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
        },
        'Trusted_Connection': 'yes',
        # Database Name not needed for test environments
        # User must be created on host server with admin and dbcreator rights
    }
}
"""

# PostgreSQL example
"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'devdb',
        'USER': 'postgres admin',
        'PASSWORD': 'postgres admin password',
        'HOST': 'hostname',
        'PORT': '5432', # PostgreSQL default
    }
}
"""



DATABASES['readonly'] = DATABASES['default']

# Test-specific settings
NOTIFICATIONS_ON = False
DEFAULT_NUMBER_FORMAT = None
AD_CLEAN_USERNAME = None
HTTP_OR_HTTPS = "http"
REVIEW_BULK = True
TIME_ZONE = 'America/Toronto'

# Selenium browser configuration for testing
# Set to True to use headless browser for testing (requires xvfb)
# Set to False to see the browser during test execution
SELENIUM_VIRTUAL_DISPLAY = False

# Test-specific password hasher for faster testing
from django.contrib.auth.hashers import BasePasswordHasher  # noqa: E402


class SimplePasswordHasher(BasePasswordHasher):
    """A simple hasher inspired by django-plainpasswordhasher"""

    algorithm = "dumb"  # This attribute is needed by the base class.

    def salt(self):
        return ""

    def encode(self, password, salt):
        return "dumb$$%s" % password

    def verify(self, password, encoded):
        algorithm, hash = encoded.split("$$", 1)
        assert algorithm == "dumb"
        return password == hash

    def safe_summary(self, encoded):
        """This is a decidedly unsafe version.

        The password is returned in the clear.
        """
        return {"algorithm": "dumb", "hash": encoded.split("$", 2)[2]}

PASSWORD_HASHERS = ("qatrack.test_settings.SimplePasswordHasher",)

AUTHENTICATION_BACKENDS = ['qatrack.accounts.backends.QATrackAccountBackend']

# Customize any of the above settings as needed for your test environment
