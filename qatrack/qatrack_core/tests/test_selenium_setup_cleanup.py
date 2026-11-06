"""A browser and its profile directory must not survive a failed setUpClass.

`SeleniumTests.setUpClass` creates two things that have to be released: a
temporary Chrome profile directory, and the driver itself - which is a browser
process. Both were released in `tearDownClass`, and `tearDownClass` does not
run when `setUpClass` raises. Everything between the two creations can raise:
the driver launch, the BiDi viewport call, and the live server's own
`setUpClass`. So one failure left a headless browser running and a
`qatrack-selenium-chrome-*` directory behind, per test class, for the rest of
the run.

Reported by @nsmela on #868 as item 7, with the fix: register both as class
cleanups where they are created, because unittest runs those whether or not
setUpClass finishes.

**No browser is started here.** `webdriver.Chrome` is patched to raise, which
is the failure being tested, so these run anywhere and are not marked
`selenium`.
"""

import pathlib
import tempfile
import unittest
from unittest import mock

from django.test import SimpleTestCase, override_settings

from qatrack.qatrack_core.tests.live import SeleniumTests

CHROME_PROFILE_GLOB = 'qatrack-selenium-chrome-*'


class _DriverFailedToStart(Exception):
    """Stands in for anything the launch can raise: a missing binary, a driver
    version mismatch, a port already taken."""


def run_one_class(test_case_class):
    """Run a TestCase class through unittest, returning its result.

    Deliberately the real machinery rather than calling setUpClass directly:
    `doClassCleanups()` is called by unittest, and whether it is called on the
    failure path is the entire property under test. Calling setUpClass by hand
    would prove nothing.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(test_case_class)
    result = unittest.TestResult()
    suite.run(result)
    return result


def chrome_profile_dirs():
    return set(pathlib.Path(tempfile.gettempdir()).glob(CHROME_PROFILE_GLOB))


@override_settings(SELENIUM_BROWSER='chromium', SELENIUM_HEADLESS=True)
class TestSetUpClassCleansUpAfterAFailure(SimpleTestCase):

    def test_the_profile_directory_is_removed_when_the_driver_fails_to_start(self):
        before = chrome_profile_dirs()

        class Probe(SeleniumTests):
            def test_never_runs(self):  # pragma: no cover - setUpClass raises first
                pass

        with mock.patch('selenium.webdriver.Chrome', side_effect=_DriverFailedToStart):
            result = run_one_class(Probe)

        assert result.errors, "setUpClass was expected to fail, and did not"
        leaked = chrome_profile_dirs() - before
        assert not leaked, "left behind: %s" % sorted(str(p) for p in leaked)

    def test_the_driver_is_quit_when_a_later_step_fails(self):
        """The driver started, and something after it did not.

        The viewport call is the realistic case - it is the first thing to run
        after the launch, and it talks to the browser over BiDi. Patched here
        to raise, so the test does not need a browser.
        """
        quit_calls = []

        class FakeDriver:
            def quit(self):
                quit_calls.append(True)

        class Probe(SeleniumTests):
            def test_never_runs(self):  # pragma: no cover - setUpClass raises first
                pass

        with mock.patch('selenium.webdriver.Chrome', return_value=FakeDriver()), \
             mock.patch.object(SeleniumTests, 'set_viewport_size',
                               side_effect=_DriverFailedToStart):
            result = run_one_class(Probe)

        assert result.errors, "setUpClass was expected to fail, and did not"
        assert quit_calls, "the driver was never quit, so a browser process was left running"

    def test_the_browser_quits_before_its_profile_directory_is_removed(self):
        """Cleanups are LIFO, and the order is load-bearing.

        Chrome writes to its profile directory until it exits. Removing the
        directory first is how you get a browser writing into a path that no
        longer exists, which on Windows is a refusal rather than a mess. The
        registration order in setUpClass - directory first, driver second -
        is what makes the run order right, and it is easy to reverse by
        accident when editing either line.
        """
        order = []

        class FakeDriver:
            def quit(self):
                order.append('quit')

        class Probe(SeleniumTests):
            def test_never_runs(self):  # pragma: no cover - setUpClass raises first
                pass

        real_rmtree = None

        def recording_rmtree(path, *args, **kwargs):
            order.append('rmtree')
            return real_rmtree(path, *args, **kwargs)

        import shutil as _shutil
        real_rmtree = _shutil.rmtree

        with mock.patch('selenium.webdriver.Chrome', return_value=FakeDriver()), \
             mock.patch.object(SeleniumTests, 'set_viewport_size',
                               side_effect=_DriverFailedToStart), \
             mock.patch('qatrack.qatrack_core.tests.live.shutil.rmtree', recording_rmtree):
            run_one_class(Probe)

        assert order == ['quit', 'rmtree'], order
