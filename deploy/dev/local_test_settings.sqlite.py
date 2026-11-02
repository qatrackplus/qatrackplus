# Test-specific settings for QATrack+ - SQLite (file-based) variant
# Copy this file to qatrack/local_test_settings.py and customize as needed

DEBUG = True
TEMPLATE_DBG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db/default.db',
        # The test database is named, and named something *other* than the
        # development one, for two separate reasons.
        #
        # Naming it at all is what gives the suite a file-backed test database
        # rather than an in-memory one: with no `TEST` name Django 4.2 uses an
        # **in-memory** database for SQLite. (An earlier version of this comment
        # said `test_db/default.db`, which is not what Django does.)
        #
        # It does **not** point the suite at a provisioned deployment, which an
        # earlier version of this comment also claimed. The name below is a
        # separate database; `make test-integration` is the only thing that
        # tests the provisioned one, and it appends its own `TEST` name to its
        # own copy of this file to do so.
        #
        # Naming it `test_sqlite.db` rather than `db/default.db` is the
        # important half. For a file-based SQLite test database Django calls
        # `os.remove` on it before creating it and again at teardown, and
        # pytest-django is non-interactive so nobody is asked. When the two
        # names matched, a plain `pytest` **deleted the developer's populated
        # database** - measured: 1.9 MB and 120 tables, gone after a four-test
        # run. Distinct names make that impossible rather than unlikely.
        #
        # `db/` must exist, since this is a file. AGENTS.md's getting-started
        # creates it; if it is missing, every database test errors with
        # `unable to open database file`, which does not mention the folder.
        'TEST': {'NAME': 'db/test_sqlite.db'},
    }
}
# `readonly` is a *copy* of `default` carrying `TEST: {'MIRROR': 'default'}`,
# rather than the same dict object. Django's test runner dedupes aliases by
# connection signature, so an alias which *is* `default` does **not** build a
# second test database - measured with `get_unique_databases_and_mirrors()`:
# one database either way, with `readonly` recorded as a second alias of it.
#
# What `MIRROR` does change is the flush. Without it a `TransactionTestCase`
# flushes `default` and `readonly` both, which is the same database twice -
# measured with `_databases_names(include_mirrors=False)`:
# `['default', 'readonly']` aliased against `['default']` mirrored. In practice
# that costs time rather than correctness; the GUI suite passes 43/43 against a
# file either way (nsmela and jackdaw, both on 2026-11-02).
#
# `MIRROR` is kept because it is Django's own shape for a replica, and because
# it is the one that stays right if `readonly` is ever pointed at another host
# or database - there the signatures differ and the runner really would build,
# and flush, a second test database.
DATABASES['readonly'] = dict(
    DATABASES['default'],
    TEST={**DATABASES['default'].get('TEST', {}), 'MIRROR': 'default'},
)

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
