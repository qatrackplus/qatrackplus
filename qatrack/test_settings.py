import importlib.util

from django.contrib.auth.hashers import BasePasswordHasher

try:
    from .settings import *  # noqa: F403,F401
except ImportError:
    pass

try:
    from .local_settings import *  # noqa: F403,F401
except ImportError:
    pass

NOTIFICATIONS_ON = False
DEFAULT_NUMBER_FORMAT = None
DEBUG = False
SELENIUM_VIRTUAL_DISPLAY = False # Set to True to use headless browser for testing (requires xvfb)
AD_CLEAN_USERNAME = None
HTTP_OR_HTTPS = "http"
REVIEW_BULK = True
TIME_ZONE = 'America/Toronto'
LANGUAGE_CODE = "en"


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

# -----------------------------------------------------------------------------
# A safe default database, so a test run needs no local_test_settings.py
#
# settings.py ships `DATABASES = {}` and this file has already imported
# local_settings.py above, so a checkout that configured neither has no database
# at all and the suite cannot start. The SQLite block below is what it falls back
# to: local, in memory, and gone when the process exits.
#
# **It is a default and not a replacement, and that distinction is the whole
# point of this block.** An earlier version assigned DATABASES unconditionally,
# which looked like a safety measure and was in fact a hole in CI: the
# PostgreSQL, MySQL and SQL Server jobs configure their engine by copying
# `deploy/<engine>/local_settings.py` into place (.github/workflows/ci.yml), and
# settings.py imports this file afterwards whenever pytest is in sys.argv. The
# three engine jobs therefore ran against SQLite, and the matrix tested one
# engine three times while reporting four. @copilot found it on c#17.
#
# What the unconditional form was protecting against is real, so it is worth
# saying what replaces it. A deployment's local_settings.py names the
# *production* database, and a suite that honours it connects to that server.
# It does not run against the production database itself: Django's test runner
# creates and drops `test_<name>` beside it, and refuses to reuse an existing
# one without being told. The exception is SQLite, where an unset TEST['NAME']
# is silently replaced by `:memory:` while a *set* one is a real file that
# `_create_test_db` erases first - which is why TEST['NAME'] is spelled out
# here, and why `deploy/dev/local_test_settings.dev.py` says never to point it
# at the development database.
#
# So: configure a database for the suite deliberately, in local_settings.py or
# local_test_settings.py, and this default stays out of the way.

if not globals().get('DATABASES', {}).get('default', {}).get('ENGINE'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
            # Stated, not inferred. Django would otherwise substitute
            # ':memory:' silently for an unset TEST['NAME'], which means the
            # database a test run uses is not the one the settings appear to
            # name.
            'TEST': {'NAME': ':memory:'},
        }
    }

# One connection is enough for a test run, whatever SQL Explorer is configured
# with: settings.py pops 'readonly' before it imports this file and points
# EXPLORER_CONNECTIONS at 'default' for the duration, so the suite neither needs
# a read-only user to exist nor asks Django to build a second test database for
# it.

# The cache, unlike the database above, is replaced outright and not defaulted.
#
# settings.py always defines one - DatabaseCache on 'qatrack_cache_table' - so
# there is no unconfigured case for a default to fill. That cache does work
# under test: Django's `create_test_db()` runs `createcachetable` after
# migrating, so the table exists in a freshly built test database. It is pinned
# to local memory anyway, so that the suite does not depend on that step, does
# not need the table in a reused database, and does not carry cached values
# between tests.
#
# The cost is that nothing here exercises the database cache, so the guarantee
# that `migrate` alone leaves a usable one belongs to qatrack_core's cache-table
# migration and a test that builds a table of its own rather than reading this
# setting.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# A missing local_test_settings.py is fine - the defaults above are safe. A
# *broken* one is not, and must not be mistaken for a missing one: a bare
# `except ImportError: pass` swallows a failing import inside the file too,
# which would silently discard a developer's own test settings and run
# something else.
if importlib.util.find_spec('qatrack.local_test_settings') is not None:
    from .local_test_settings import *  # noqa: F403,F401
