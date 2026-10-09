import socket
import threading
import time
import urllib.request

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

    def test_no_name_mangled_method_is_left_in_the_class(self):
        mangled = [name for name in vars(live.LiveServerSingleThread) if name.startswith('_LiveServerSingleThread__')]
        assert mangled == [], (
            '%s: a double-underscore method name is mangled inside a class body and overrides nothing' % mangled
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
