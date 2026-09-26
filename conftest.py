import os
import pathlib

import pytest

# The older idiom for excluding GUI tests. Still honoured (see
# pytest_collection_modifyitems) but deprecated in 4.0 for removal in 4.2:
# the space needs quoting on every shell, and plain `pytest` now does it.
_DEPRECATED_EXCLUDE_MARKEXPR = 'not selenium'


def pytest_addoption(parser):
    parser.addoption(
        '--run-selenium',
        action='store_true',
        default=False,
        help=(
            "Also run the GUI (Selenium/browser) tests, which need a real "
            "Chromium or Firefox installed on the host. Skipped by default."
        ),
    )


def pytest_configure(config):
    markexpr = (config.getoption('markexpr') or '').strip()
    if markexpr == _DEPRECATED_EXCLUDE_MARKEXPR:
        config.issue_config_time_warning(
            pytest.PytestDeprecationWarning(
                'pytest -m "not selenium" is deprecated - GUI/Selenium tests '
                'are now skipped by default, so plain `pytest` does the same '
                'thing without the quoting. This form still works today but '
                'will be removed in QATrack+ 4.2; switch to plain `pytest` '
                '(or `pytest --run-selenium` to also run the GUI tests).'
            ),
            stacklevel=2,
        )


def pytest_sessionstart(session):
    """Refuse the run if it is not on the database it was told to be on.

    Deliberately `pytest_sessionstart` and not `pytest_report_header`: the
    header hook does not run when pytest is quiet, and `addopts = "-ra -q"`
    makes every run quiet. A guard that silently does not execute is worse than
    no guard, because it reads as a pass.

    Set QATRACK_EXPECTED_DB_VENDOR to the vendor a run is supposed to use -
    'postgresql', 'mysql', 'microsoft' or 'sqlite' - and the session aborts
    unless that is what it got.

    This exists because CI spent an unknown number of runs testing nothing. The
    database jobs write `qatrack/local_settings.py` and nothing else, while
    `qatrack/test_settings.py` replaces DATABASES with in-memory SQLite whenever
    `qatrack/local_test_settings.py` is absent. Every Postgres, MySQL and SQL
    Server row therefore ran on in-memory SQLite and passed, and the only trace
    was one RuntimeWarning in a summary nobody reads.

    A green tick that means "we did not test this" is worse than a red one, so
    the intent is now declared by the caller and checked here rather than
    inferred. `vendor` is Django's own name for the backend, which is why the SQL
    Server value is 'microsoft'.
    """
    import os as _os

    from django.db import connection

    vendor = connection.vendor
    name = connection.settings_dict.get('NAME')
    expected = _os.environ.get('QATRACK_EXPECTED_DB_VENDOR')

    if expected:
        if vendor != expected:
            raise pytest.UsageError(
                'QATRACK_EXPECTED_DB_VENDOR=%s but this run is on %r (NAME=%r).\n'
                'Nothing was tested against %s. The usual cause is a missing '
                'qatrack/local_test_settings.py: test_settings.py then falls back '
                'to in-memory SQLite and discards whatever local_settings.py '
                'configured.' % (expected, vendor, name, expected)
            )
        print('database: vendor=%s name=%s (expected %s) - ok'
              % (vendor, name, expected))


SCREENSHOT_DIR = pathlib.Path(__file__).parent / 'selenium-screenshots'


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Save a browser screenshot when a Selenium test fails.

    Adapted from copilot/selenium-modern-implementation, which had this and we
    did not. A failed GUI test otherwise leaves nothing behind: the traceback
    says an element was not found, but not what the page actually looked like
    at that moment. That matters most in CI, where re-running locally may not
    reproduce it - the Chromium timing flakes being the obvious example.

    The image itself is captured by SeleniumTests.tearDown rather than here.
    This hook does not run until the whole unittest lifecycle is over, and
    that tearDown navigates to about:blank, so capturing at this point would
    reliably save a blank page. Here we only decide whether to keep it.
    """
    outcome = yield
    report = outcome.get_result()

    if report.when != 'call' or not report.failed:
        return

    # item.instance is set for unittest.TestCase-based tests, which is what
    # the Selenium suite uses. Non-GUI tests have neither attribute below and
    # so are unaffected.
    instance = getattr(item, 'instance', None)
    png = getattr(instance, '_failure_screenshot_png', None)

    if png is None:
        # tearDown never ran (a failure in setUpClass/setUp, say). The driver
        # may still be showing something useful, so try it live.
        driver = getattr(instance, 'driver', None)
        if driver is None:
            return
        try:
            png = driver.get_screenshot_as_png()
        except Exception:  # noqa: BLE001 - see below
            return

    safe_name = item.nodeid.replace('/', '_').replace('::', '__').replace(' ', '_')
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        (SCREENSHOT_DIR / ('%s.png' % safe_name)).write_bytes(png)
    except OSError:
        # The test has already failed; an error while saving evidence about
        # it should not replace the real failure in the report.
        pass


def pytest_collection_modifyitems(config, items):
    # Auto-skip only on a plain invocation. An explicit -m/--markexpr from
    # the caller is their selection to make, not ours to second-guess.
    if config.getoption('--run-selenium') or config.getoption('markexpr'):
        return

    skip_selenium = pytest.mark.skip(
        reason="GUI test - needs a real browser; pass --run-selenium (or select explicitly with -m) to run it"
    )
    for item in items:
        if 'selenium' in item.keywords:
            item.add_marker(skip_selenium)


@pytest.fixture(autouse=True, scope='session')
def _xdist_worker_media_root(tmp_path_factory):
    """Give each xdist worker its own MEDIA_ROOT.

    pytest-django already hands each worker a separate test database, and
    LiveServerTestCase already binds a free port per instance, so the
    database and the web server are isolated for free. The filesystem is
    not: MEDIA_ROOT, UPLOAD_ROOT and TMP_UPLOAD_ROOT all point inside
    qatrack/media, which every worker would otherwise write to at once -
    upload tests clobbering each other's files, and tmp uploads being
    cleaned up out from under a different worker.

    Redirecting them per worker is what makes `-n` safe. Outside xdist
    (PYTEST_XDIST_WORKER unset) this is a no-op, so a serial run still
    uses the real media directory exactly as before.
    """
    worker = os.environ.get('PYTEST_XDIST_WORKER')
    if not worker:
        yield
        return

    from django.test import override_settings

    root = tmp_path_factory.mktemp('media-%s' % worker)
    uploads = root / 'uploads'
    tmp_uploads = uploads / 'tmp'
    tmp_uploads.mkdir(parents=True, exist_ok=True)

    with override_settings(
        MEDIA_ROOT=str(root),
        UPLOAD_ROOT=str(uploads),
        TMP_UPLOAD_ROOT=str(tmp_uploads),
    ):
        yield
