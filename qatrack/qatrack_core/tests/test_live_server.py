import pathlib
import re
import socket
import threading
import time
import urllib.request

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import SimpleTestCase, override_settings
from django.urls import path

from qatrack.qatrack_core.tests import live

_in_view = {'now': 0, 'most': 0}
_in_view_lock = threading.Lock()


def slow_view(request):
    """Holds the request for a moment and records how many requests were inside a view at once."""
    with _in_view_lock:
        _in_view['now'] += 1
        _in_view['most'] = max(_in_view['most'], _in_view['now'])
    time.sleep(0.2)
    with _in_view_lock:
        _in_view['now'] -= 1
    return HttpResponse('ok')


urlpatterns = [path('slow/', slow_view)]


class TestLiveServerClass(SimpleTestCase):
    """The GUI tests' live server must be the one-request-at-a-time server.

    StaticLiveServerSingleThreadedTestCase exists to work around Django ticket
    #29062: with an in-memory SQLite test database, Django's threaded live server
    hands one database connection to every request thread, and a page that makes
    several requests at once corrupts it. From 2019 the class did nothing, because
    its override was called `__create_server`. Inside a class body Python renames a
    double-underscore method to `_LiveServerSingleThread__create_server`, a name
    Django never calls, so every GUI test ran on Django's threaded server and no
    test noticed. These tests notice.
    """

    def test_the_gui_tests_get_the_one_request_at_a_time_server(self):
        assert live.LiveServerSingleThread.server_class is live.OneRequestAtATimeWSGIServer

    def test_the_gui_tests_base_class_actually_uses_it(self):
        """The test above checks the thread class; this checks that anything reaches it.

        Both were needed. From the headless work until 2026-11-01, SeleniumTests
        subclassed StaticLiveServerTestCase directly, so LiveServerSingleThread was
        correctly built, correctly documented, asserted on by the test above - and
        reached by no test at all. Django's own LiveServerThread served every GUI
        test, which is the second time this machinery has been inert without a
        failure to show for it. Nathan Smela found it on review, 2026-10-09 and
        again 2026-10-30.
        """
        assert live.SeleniumTests.server_thread_class is live.LiveServerSingleThread
        assert issubclass(live.SeleniumTests, live.StaticLiveServerSingleThreadedTestCase)

    def test_no_name_mangled_method_is_left_in_the_class(self):
        mangled = [name for name in vars(live.LiveServerSingleThread) if name.startswith('_LiveServerSingleThread__')]
        assert mangled == [], (
            '%s: a double-underscore method name is mangled inside a class body and overrides nothing' % mangled
        )


class TestBrowserSetting(SimpleTestCase):
    """SELENIUM_BROWSER must pick a browser or stop the run, never fall through.

    Every branch in live.py tested `== 'chromium'`, so any other value ran Firefox
    and the suite passed - which is how a Windows reader asking for `chrome` got a
    Firefox run on 2026-11-01 and no indication of it.
    """

    def test_the_two_real_values_resolve_to_themselves(self):
        assert live.resolve_browser_setting('firefox') == 'firefox'
        assert live.resolve_browser_setting('chromium') == 'chromium'

    def test_chrome_is_accepted_as_chromium(self):
        """Same driver, same handling, and the natural spelling on Windows."""
        assert live.resolve_browser_setting('chrome') == 'chromium'

    def test_edge_is_its_own_value_in_the_chromium_family(self):
        """Not an alias: Edge needs msedgedriver, and chromedriver will not drive it."""
        assert live.resolve_browser_setting('edge') == 'edge'
        assert 'edge' in live.CHROMIUM_FAMILY

    def test_case_and_surrounding_space_do_not_matter(self):
        """It usually arrives from the environment, where both are easy to add."""
        assert live.resolve_browser_setting('  Chromium \n') == 'chromium'
        assert live.resolve_browser_setting('FIREFOX') == 'firefox'

    def test_an_unrecognised_value_stops_the_run(self):
        """The examples are derived, not listed, and that is the point.

        This test used to try `('safari', 'chrom', 'edge', '', None)`. When Edge
        was added to the harness, `'edge'` started resolving and the test failed
        - correctly, but by then the list had become a second place where the
        supported set was written down. Taking the candidates from
        SELENIUM_BROWSERS means the next browser cannot quietly turn one of
        these assertions into a no-op.
        """

        unsupported = [
            value for value in ('msedge', 'safari', 'chrom', 'webkitgtk', 'ie', 'lynx')
            if value not in live.SELENIUM_BROWSERS
        ]
        assert unsupported, 'every example is now supported - add an unsupported one'
        for value in unsupported + ['', None]:
            with self.subTest(value=value):
                with self.assertRaises(ImproperlyConfigured):
                    live.resolve_browser_setting(value)

    def test_the_message_names_what_was_asked_for_and_what_is_allowed(self):
        """The whole point is that the reader learns which value was wrong."""
        with self.assertRaises(ImproperlyConfigured) as caught:
            live.resolve_browser_setting('safari')
        message = str(caught.exception)
        assert 'safari' in message
        for allowed in sorted(live.SELENIUM_BROWSERS):
            assert allowed in message, '%r is accepted but not offered: %s' % (allowed, message)

    def test_the_setting_is_read_in_exactly_one_place(self):
        """Guard the guard: a new branch on the raw setting would undo this.

        The resolver only helps while every branch runs on its output. A second
        `getattr(settings, 'SELENIUM_BROWSER')` anywhere in the module would put the
        unvalidated string back into a comparison, which is the shape that let
        `chrome` run Firefox. Asserted on the settings read itself, not on mentions
        of the name, so comments and the error message do not register.
        """
        source = pathlib.Path(live.__file__).read_text(encoding='utf-8').splitlines()
        reads = [
            (n, line.strip())
            for n, line in enumerate(source, 1)
            if "getattr(settings, 'SELENIUM_BROWSER'" in line
        ]
        assert reads, 'live.py no longer reads SELENIUM_BROWSER at all - has it moved?'
        unresolved = [(n, line) for n, line in reads if 'resolve_browser_setting' not in line]
        assert not unresolved, (
            'live.py reads SELENIUM_BROWSER without passing it through '
            'resolve_browser_setting(): %r' % unresolved
        )

    def test_no_branch_compares_against_a_value_the_resolver_cannot_return(self):
        """`== 'chrome'` would be dead code, since the resolver maps it to 'chromium'.

        What counts as reachable is whatever `resolve_browser_setting` can
        return - the *values* of the map, not its keys - so this reads them from
        the map rather than naming them. It used to name `'chromium'` and
        `'firefox'`, which made `== 'edge'` look like dead code the day Edge
        became real.
        """

        returnable = set(live.SELENIUM_BROWSERS.values())
        source = pathlib.Path(live.__file__).read_text(encoding='utf-8').splitlines()
        dead = [
            (n, line.strip())
            for n, line in enumerate(source, 1)
            for value in re.findall(r"browser_setting == '([^']*)'", line)
            if value not in returnable
        ]
        assert not dead, 'these comparisons can never be true: %r' % dead
        unreachable = set(live.CHROMIUM_FAMILY) - returnable
        assert not unreachable, (
            'CHROMIUM_FAMILY names values the resolver never returns: %r' % unreachable
        )


@override_settings(ROOT_URLCONF=__name__, MIDDLEWARE=[])
class TestLiveServerBehaviour(live.StaticLiveServerSingleThreadedTestCase):
    """The two promises, checked on the server a GUI test actually gets."""

    def fetch(self, timeout):
        # 127.0.0.1 rather than live_server_url's localhost: on Windows, localhost tries ::1
        # first, and the refused IPv6 connection costs about 2 s before the IPv4 one is made,
        # which would swamp what these tests measure. MIDDLEWARE is empty, so no Host check.
        url = 'http://127.0.0.1:%d/slow/' % self.server_thread.port
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read()

    def test_parallel_requests_never_overlap_in_django(self):
        """Django sees one request at a time, so the shared connection is never used twice at once."""
        _in_view.update(now=0, most=0)
        bodies, errors = [], []

        def fetch():
            try:
                bodies.append(self.fetch(timeout=20))
            except Exception as e:  # noqa: BLE001 - reported below
                errors.append(repr(e))

        threads = [threading.Thread(target=fetch) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [] and bodies == [b'ok'] * 5, errors
        assert _in_view['most'] == 1, '%d requests were inside a view at once' % _in_view['most']

    def test_an_idle_connection_does_not_hold_up_other_requests(self):
        """Browsers open connections before they use them; one sending nothing must not block the server."""
        idle = socket.create_connection(('127.0.0.1', self.server_thread.port))
        try:
            started = time.monotonic()
            body = self.fetch(timeout=10)
            took = time.monotonic() - started
        finally:
            idle.close()
        assert body == b'ok'
        assert took < 2, 'a request waited %.1f s behind a connection that sent nothing' % took
