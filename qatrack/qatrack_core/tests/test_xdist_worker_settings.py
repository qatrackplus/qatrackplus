"""A pytest-xdist worker must load test_settings, the same as a serial run.

`settings.py` decides whether it is under pytest so it knows whether to import
`test_settings`. It used to ask `sys.argv`, which works for a normal run and
cannot work in a worker: xdist spawns a *fresh interpreter* whose argv is
`['-c']`. So every `-n` run silently used the developer's real settings -
PBKDF2 password hashing instead of the fast test hasher, and the configured
database instead of the test one.

It is not a cosmetic difference. The Windows validation measured 673s of
per-test time at `-n 4` against 202s serially, which is what real password
hashing costs. And because `conftest.py` already redirects MEDIA_ROOT per
worker off `PYTEST_XDIST_WORKER`, parallel runs had per-worker media but
shared, wrong settings - the half-isolated state is worse than either.

These assert on the settings themselves rather than on timing, so they mean
the same thing on any machine. Under `-n` they run inside a worker, which is
the case being protected; run serially they still check the ordinary path.
"""

import os

from django.conf import settings
from django.test import SimpleTestCase

from qatrack.settings import _is_pytest_run


class TestWorkerLoadsTestSettings(SimpleTestCase):

    def test_test_settings_are_applied(self):
        """Fails in a worker if settings.py did not detect the pytest run."""
        where = os.environ.get('PYTEST_XDIST_WORKER', 'serial run')
        hasher = settings.PASSWORD_HASHERS[0]
        assert 'SimplePasswordHasher' in hasher, (
            "%s did not load test_settings: PASSWORD_HASHERS[0] is %s. "
            "settings.py failed to detect that it is under pytest."
            % (where, hasher)
        )

    def test_notifications_are_off(self):
        """A second setting from test_settings, so one stray default cannot pass."""
        assert settings.NOTIFICATIONS_ON is False


class TestPytestDetection(SimpleTestCase):
    """`_is_pytest_run()` has to answer for both interpreters."""

    def test_detects_the_current_run(self):
        assert _is_pytest_run()

    def test_detects_a_worker_whose_argv_says_nothing(self):
        from unittest import mock

        with mock.patch.object(__import__('sys'), 'argv', ['-c']):
            with mock.patch.dict(os.environ, {'PYTEST_XDIST_WORKER': 'gw0'}):
                assert _is_pytest_run(), "a worker must be detected via the env var"

    def test_is_false_outside_pytest(self):
        from unittest import mock

        with mock.patch.object(__import__('sys'), 'argv', ['manage.py', 'runserver']):
            env = {k: v for k, v in os.environ.items() if k != 'PYTEST_XDIST_WORKER'}
            with mock.patch.dict(os.environ, env, clear=True):
                assert not _is_pytest_run(), "a plain manage.py run must not look like pytest"
