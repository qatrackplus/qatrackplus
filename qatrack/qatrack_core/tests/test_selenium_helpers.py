"""click_by_css_selector's two failure paths, without a browser.

An element that is covered and an element that has been replaced both arrive
as a WebDriverException and need opposite handling: the first wants a JS
click that ignores overlays, the second wants to be found again. Getting
them the wrong way round is silent - JS-clicking a dead reference raises the
same staleness error one line lower, so the failure reads as though the
fallback broke rather than as a stale element.

The real trigger is a date picker still closing while `.open .today` is
matched against it, which is timing-dependent and does not reproduce on
demand. This drives each path directly instead.
"""
from django.test import SimpleTestCase
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as e_c
from selenium.webdriver.support.wait import WebDriverWait

from qatrack.qatrack_core.tests.live import (
    SeleniumTests,
    ajax_settled,
    explicit_find_element,
)


class _Element:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.clicked = False

    def click(self):
        if self.behaviour == 'stale':
            raise StaleElementReferenceException("element is not attached")
        if self.behaviour == 'intercepted':
            raise ElementClickInterceptedException("element click intercepted")
        self.clicked = True


class _Driver:
    """Hands out an element per find_element call, per the script given."""

    def __init__(self, *behaviours):
        self.behaviours = list(behaviours)
        self.found = []
        self.js_clicks = []

    def find_element(self, by, value):
        behaviour = self.behaviours.pop(0) if self.behaviours else 'ok'
        element = _Element(behaviour)
        self.found.append(element)
        return element

    def execute_script(self, script, *args):
        self.js_clicks.append(args)


class _Harness:
    """Enough of SeleniumTests for the helper under test."""

    def __init__(self, driver):
        self.driver = driver
        self.scrolls = 0

    def scroll_into_view_css(self, css_sel):
        self.scrolls += 1


def _click(driver):
    harness = _Harness(driver)
    SeleniumTests.click_by_css_selector(harness, ".open .today")
    return harness


class TestClickReFindsAStaleElement(SimpleTestCase):

    def test_a_stale_element_is_found_again_and_clicked(self):
        driver = _Driver('stale', 'ok')
        _click(driver)

        assert len(driver.found) == 2, "did not re-find after staleness"
        assert driver.found[1].clicked
        assert driver.js_clicks == [], "JS-clicked a dead reference"

    def test_it_rescrolls_before_each_attempt(self):
        """The element moved; its position is not assumed to have survived."""
        harness = _click(_Driver('stale', 'ok'))
        assert harness.scrolls == 2

    def test_it_gives_up_rather_than_spinning(self):
        driver = _Driver('stale', 'stale', 'stale')
        with self.assertRaises(StaleElementReferenceException):
            _click(driver)
        assert len(driver.found) == 3


class TestClickFallsBackForACoveredElement(SimpleTestCase):

    def test_an_intercepted_click_uses_javascript(self):
        driver = _Driver('intercepted')
        _click(driver)

        assert len(driver.js_clicks) == 1, "did not fall back to a JS click"
        assert driver.js_clicks[0] == (driver.found[0],)
        assert len(driver.found) == 1, "retried instead of falling back"

    def test_interception_is_not_retried(self):
        """Re-finding a covered element just finds the same covered element."""
        driver = _Driver('intercepted', 'ok')
        _click(driver)
        assert len(driver.found) == 1


class TestTheOrdinaryCase(SimpleTestCase):

    def test_a_clickable_element_is_clicked_directly(self):
        driver = _Driver('ok')
        _click(driver)

        assert driver.found[0].clicked
        assert driver.js_clicks == []
        assert len(driver.found) == 1


class _MissingDriver:
    """find_element never succeeds, which is the timeout path."""

    def __init__(self, behaviour='missing'):
        self.behaviour = behaviour
        self.calls = 0

    def find_element(self, *args, **kwargs):
        self.calls += 1
        if self.behaviour == 'missing':
            raise NoSuchElementException("nope")
        if self.behaviour == 'stale-once' and self.calls == 1:
            raise StaleElementReferenceException("stale")
        return 'element'


class TestExplicitFindElement(SimpleTestCase):
    """The patched find_element must fail as NoSuchElement, not Timeout.

    Conditions like presence_of_element_located call find_element internally.
    A TimeoutException raised inside one of those propagates through the
    surrounding WebDriverWait untouched, because that wait only ignores
    NoSuchElementException - so the message the call site passed to
    `.until(..., "waiting for X")` is discarded and the failure reads as an
    anonymous find_element timeout. Every wait message in the suite depends on
    this distinction.
    """

    def patched(self, driver, timeout=0):
        return explicit_find_element(driver, driver.find_element, timeout)

    def test_missing_element_raises_no_such_element(self):
        driver = _MissingDriver()
        with self.assertRaises(NoSuchElementException):
            self.patched(driver)(By.ID, 'absent')

    def test_timeout_is_not_what_escapes(self):
        driver = _MissingDriver()
        try:
            self.patched(driver)(By.ID, 'absent')
        except NoSuchElementException:
            pass
        except TimeoutException:
            self.fail("TimeoutException escaped; outer wait messages will be lost")

    def test_message_names_the_locator_and_timeout(self):
        driver = _MissingDriver()
        with self.assertRaises(NoSuchElementException) as caught:
            self.patched(driver)(By.ID, 'absent')
        message = str(caught.exception)
        assert 'absent' in message
        assert 'find_element' in message

    def test_original_cause_is_kept(self):
        driver = _MissingDriver()
        with self.assertRaises(NoSuchElementException) as caught:
            self.patched(driver)(By.ID, 'absent')
        assert isinstance(caught.exception.__cause__, TimeoutException)

    def test_a_call_site_message_survives_the_inner_wait(self):
        """The whole point: the outer wait gets to report its own message."""
        driver = _MissingDriver()
        driver.find_element = self.patched(driver)
        with self.assertRaises(TimeoutException) as caught:
            WebDriverWait(driver, 0).until(
                e_c.presence_of_element_located((By.ID, 'absent')),
                "the thing the test was actually waiting for",
            )
        assert "the thing the test was actually waiting for" in str(caught.exception)

    def test_success_passes_through(self):
        driver = _MissingDriver('found')
        assert self.patched(driver)(By.ID, 'present') == 'element'

    def test_stale_is_retried_not_raised(self):
        driver = _MissingDriver('stale-once')
        assert self.patched(driver, timeout=5)(By.ID, 'flaky') == 'element'
        assert driver.calls == 2


class _ScriptDriver:
    """Returns a canned [has_jquery, active, readyState] per call."""

    def __init__(self, *states):
        self.states = list(states)
        self.calls = 0

    def execute_script(self, script, *args):
        self.calls += 1
        return self.states.pop(0) if self.states else self.states_last

    @property
    def states_last(self):
        raise AssertionError("ajax_settled polled more times than expected")


class TestAjaxSettled(SimpleTestCase):
    """A page whose jQuery has not loaded yet is not a page without jQuery.

    The previous form answered True for both, so on a page still fetching its
    scripts wait_for_ajax returned immediately and the next line ran `$(...)`
    against a document where `$` did not exist - the `$ is not defined`
    failure at select_unit.
    """

    def test_jquery_busy_is_not_settled(self):
        assert ajax_settled(_ScriptDriver([True, 2, 'complete'])) is False

    def test_jquery_idle_is_settled(self):
        assert ajax_settled(_ScriptDriver([True, 0, 'complete'])) is True

    def test_jquery_idle_while_still_loading_is_settled(self):
        # jQuery is present and quiet; the document still finishing is fine.
        assert ajax_settled(_ScriptDriver([True, 0, 'interactive'])) is True

    def test_missing_jquery_mid_load_is_not_settled(self):
        """The regression this exists for."""
        assert ajax_settled(_ScriptDriver([False, -1, 'loading'])) is False
        assert ajax_settled(_ScriptDriver([False, -1, 'interactive'])) is False

    def test_missing_jquery_after_load_is_settled(self):
        # A page that genuinely does not use jQuery must not hang.
        assert ajax_settled(_ScriptDriver([False, -1, 'complete'])) is True

    def test_one_round_trip_per_poll(self):
        driver = _ScriptDriver([True, 0, 'complete'])
        ajax_settled(driver)
        assert driver.calls == 1
