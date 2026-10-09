import shutil
import time
from contextlib import contextmanager
from functools import wraps
from importlib import import_module

import pytest
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.servers.basehttp import WSGIServer
from django.test.testcases import LiveServerThread, QuietWSGIRequestHandler
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as e_c
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait


# From http://stackoverflow.com/a/20559494
def retry_if_exception(ex, max_retries, sleep_time=None, reraise=True):

    def outer(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            assert max_retries > 0
            x = max_retries
            while x:
                try:
                    return func(*args, **kwargs)
                except:  # noqa: E722
                    x -= 1
                    if x == 0 and reraise:
                        raise
                if sleep_time is not None:
                    time.sleep(sleep_time)

        return wrapper

    return outer


@retry_if_exception(WebDriverException, 5, sleep_time=1)
def WebElement_click(self):
    """
    Monkey patches the element click command to work around issue with
    later versions of webdrivers that won't click on an element if it
    is not in view
    """
    self.parent.execute_script("arguments[0].scrollIntoView();", self)
    return self._execute(Command.CLICK_ELEMENT)


WebElement.click = WebElement_click  # noqa: E305

orig_send_keys = WebElement.send_keys


@retry_if_exception(WebDriverException, 5, sleep_time=1)  # noqa: E302
def WebElement_send_keys(self, keys):
    """Monky patch send_keys to ensure element is in view"""
    self.parent.execute_script("arguments[0].scrollIntoView();", self)
    return orig_send_keys(self, keys)


WebElement.send_keys = WebElement_send_keys  # noqa: E305


# Following two classes are trying to work around this issue:
# https://code.djangoproject.com/ticket/29062#no2
class LiveServerSingleThread(LiveServerThread):
    """Runs a single threaded server rather than multi threaded. Reverts https://github.com/django/django/pull/7832"""

    def __create_server(self):
        return WSGIServer((self.host, self.port), QuietWSGIRequestHandler, allow_reuse_address=False)


class StaticLiveServerSingleThreadedTestCase(StaticLiveServerTestCase):
    "A thin sub-class which only sets the single-threaded server as a class"
    server_thread_class = LiveServerSingleThread

    static_handler = StaticFilesHandler


@pytest.mark.selenium
class SeleniumTests(StaticLiveServerSingleThreadedTestCase):

    @classmethod
    def setUpClass(cls):
        use_virtual_display = getattr(settings, 'SELENIUM_VIRTUAL_DISPLAY', False)
        browser_setting = getattr(settings, 'SELENIUM_BROWSER', 'firefox')

        if use_virtual_display:
            # Make sure xvfb is installed
            from pyvirtualdisplay import Display
            cls.display = Display(visible=0, size=(1920, 1080))
            cls.display.start()
        else:
            cls.display = None

        if browser_setting == 'chromium':
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService

            chromium_driver_path = getattr(settings, 'SELENIUM_CHROMIUM_DRIVER_PATH', '')
            chrome_options = ChromeOptions()
            if use_virtual_display:
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')

            if chromium_driver_path:
                service = ChromeService(executable_path=chromium_driver_path)
                cls.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                cls.driver = webdriver.Chrome(options=chrome_options)
        else:
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService

            ff_options = FirefoxOptions()
            if use_virtual_display:
                ff_options.add_argument('--headless')
            else:
                ff_options.add_argument('--disable-headless')

            firefox_driver_path = getattr(settings, 'SELENIUM_FIREFOX_DRIVER_PATH', '')
            if firefox_driver_path:
                service = FirefoxService(executable_path=firefox_driver_path)
            else:
                # Try to use system geckodriver
                service = FirefoxService(executable_path=shutil.which('geckodriver'))
                
            cls.driver = webdriver.Firefox(service=service, options=ff_options)

        orig_find_element = cls.driver.find_element

        @retry_if_exception(WebDriverException, 2, sleep_time=1)
        def WebElement_find_element(*args, **kwargs):
            """Monky patch find element to allow retries"""
            return orig_find_element(*args, **kwargs)

        cls.driver.find_element = WebElement_find_element

        cls.driver.set_page_load_timeout(2)
        cls.driver.implicitly_wait(2)

        cls.driver.set_window_position(0, 0)
        cls.driver.set_window_size(1920, 1080)
        cls.wait = WebDriverWait(cls.driver, 2)

        super().setUpClass()

    @classmethod
    def maximize(cls):

        if getattr(settings, 'SELENIUM_VIRTUAL_DISPLAY', False):
            for i in range(5):
                try:
                    cls.driver.maximize_window()
                    return
                except WebDriverException:
                    time.sleep(1)

        cls.driver.set_window_size(1920, 1080)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        if cls.display:
            cls.display.stop()
        super().tearDownClass()

    def tearDown(self):
        self.driver.get("about:blank")
        super().tearDown()

    @contextmanager
    def wait_for_page_load(self, timeout=2):
        old_page = self.driver.find_element(By.TAG_NAME, 'html')
        yield
        WebDriverWait(self.driver, timeout).until(staleness_of(old_page))

    @retry_if_exception(Exception, 2, sleep_time=1)
    def open(self, url):
        with self.wait_for_page_load():
            self.driver.execute_script("window.location.href='%s%s'" % (self.live_server_url, url))

    def force_login(self, user, backend=None):
        """Authenticate `user` in the browser without using a login form.

        Builds the session server-side exactly as django.contrib.auth.login()
        does, then hands the browser its cookie. The equivalent of
        django.test.Client.force_login(), which the non-browser tests already
        use - 52 call sites of client.login()/force_login() in this suite, none
        of which post the login form either.

        **Why not type the password.** Every browser test used to log in through
        the real form as `user` / `password`, and that is a credential Chrome
        recognises as found in a data breach, so it answered the login with its
        "Change your password" dialog. Browser-level dialogs are invisible to
        WebDriver - they are not in the DOM and not in the alert stack, so a
        screenshot does not show them either - and the test fails further down
        looking for a page element the dialog is covering. crane measured one
        such test at 5 of 15 with the password manager on against 5 of 5 with it
        off, 2026-10-09.

        Suppressing that dialog is a blocklist against the browser UI we have
        met. Not typing a password removes the surface: no breach dialog, no
        "Save login?", no autofill, and nothing for a future browser release to
        add. It is also faster - no form round trip, and no wait on the
        logged-in navbar - across the 27 call sites that used to log in.

        **What this deliberately stops testing** is the login page itself: form
        rendering, the POST handler and the redirect. Nothing else in the suite
        covers those, so a test that drives the real form is kept alongside
        this - see login_through_form() in qatrack/qa/tests/test_selenium.py.

        Only safe under TransactionTestCase, which these tests use: the session
        row has to be committed before the live server thread, on its own
        connection, can read it. Under plain TestCase it would sit inside the
        test's open transaction and the browser would arrive unauthenticated.
        """
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore()
        session[SESSION_KEY] = user._meta.pk.value_to_string(user)
        session[BACKEND_SESSION_KEY] = backend or settings.AUTHENTICATION_BACKENDS[0]
        session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        session.save()

        if not session.session_key:
            # Signed-cookie sessions keep their data in the cookie and have no
            # key to hand over. Say so here rather than letting every test fail
            # as "not logged in" with nothing pointing at the session backend.
            raise RuntimeError(
                "force_login() needs a session backend with a session key; "
                "%s does not provide one" % settings.SESSION_ENGINE
            )

        # add_cookie() only applies to the document's own origin, so the
        # browser has to be on the site before the cookie can be set. The login
        # page is the cheapest page that is guaranteed to render for an
        # anonymous visitor.
        self.driver.get('%s/accounts/login/' % self.live_server_url)
        self.driver.add_cookie({
            'name': settings.SESSION_COOKIE_NAME,
            'value': session.session_key,
            'path': settings.SESSION_COOKIE_PATH or '/',
        })

        # The browser is authenticated but still showing the anonymous login
        # page; every caller navigates next, which is why nothing is loaded
        # here. The form-based version landed on LOGIN_REDIRECT_URL, and no
        # caller relied on that either.

    def wait_for_success(self):
        self.wait.until(
            e_c.presence_of_element_located((By.XPATH, '//ul[@class = "messagelist"]/li[@class = "success"]'))
        )

    def scroll_into_view(self, el_id):
        self.wait.until(e_c.presence_of_element_located((By.ID, el_id)))
        actions = ActionChains(self.driver)
        element = self.driver.find_element(By.ID, el_id)
        actions.move_to_element(element)
        time.sleep(1)
        try:
            actions.perform()
            self.driver.find_element(By.CSS_SELECTOR, "body").click()
            self.driver.execute_script("window.scrollTo(0, -200);")
        except:  # noqa: E722
            pass

    def scroll_into_view_css(self, css_sel):
        self.wait.until(e_c.presence_of_element_located((By.CSS_SELECTOR, css_sel)))
        actions = ActionChains(self.driver)
        element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
        actions.move_to_element(element)
        time.sleep(1)
        try:
            actions.perform()
            self.driver.execute_script("window.scrollTo(0, -200);")
        except:  # noqa: E722
            pass

    def select_by_index(self, el_id, index):
        """Set force_select2= True when selecting a 0 index for a select2 element"""

        self.scroll_into_view(el_id)
        try:
            # select2?
            sel2 = self.driver.find_element(By.ID, "select2-%s-container" % el_id)
            sel2.click()
            time.sleep(0.1)
            els = self.driver.find_elements(By.CLASS_NAME, "select2-results__option")
            els[index].click()
        except:  # noqa: E722
            select_el = self.driver.find_element(By.ID, el_id)
            select = Select(select_el)
            try:
                select.select_by_index(index)
            except WebDriverException:
                val = select.options[index].get_attribute("value")
                self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", select_el, val)

    def select_by_text(self, el_id, text):

        self.scroll_into_view(el_id)
        try:
            select_el = self.driver.find_element(By.ID, el_id)
            select = Select(select_el)
            try:
                select.select_by_visible_text(text)
            except WebDriverException:
                found = False
                for opt in select.options:
                    if opt.text == text:
                        self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", select_el, opt.get_attribute("value"))
                        found = True
                        break
                if not found:
                    raise Exception("Option with text '%s' not found" % text)
        except WebDriverException:

            sel2 = self.driver.find_element(By.ID, "select2-%s-container" % el_id)
            sel2.click()

            els = self.driver.find_elements(By.CLASS_NAME, "select2-results__option")
            for el in els:
                if el.text == text:
                    el.click()
                    break

    def select_by_value(self, el_id, val):

        self.scroll_into_view(el_id)
        try:
            select_el = self.driver.find_element(By.ID, el_id)
            select = Select(select_el)
            try:
                select.select_by_value(val)
            except WebDriverException:
                found = False
                for opt in select.options:
                    if opt.get_attribute("value") == val:
                        self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", select_el, val)
                        found = True
                        break
                if not found:
                    raise Exception("Option with value '%s' not found" % val)
        except WebDriverException:

            sel2 = self.driver.find_element(By.ID, "select2-%s-container" % el_id)
            sel2.click()

            els = self.driver.find_elements(By.CLASS_NAME, "select2-results__option")
            for el in els:
                if el.get_attribute('id').endswith(val):
                    el.click()
                    break

    def send_keys(self, el_id, text):
        for i in range(3):
            try:
                self.scroll_into_view(el_id)
                self.driver.find_element(By.ID, el_id).send_keys(text)
                break
            except:  # noqa: E722
                if i == 2:
                    raise
                else:
                    time.sleep(1)

    def click(self, el_id, scroll=True):
        if scroll:
            self.scroll_into_view(el_id)
        element = self.driver.find_element(By.ID, el_id)
        try:
            element.click()
        except:  # noqa: E722
            self.driver.execute_script("arguments[0].click();", element)

    def click_by_css_selector(self, css_sel):
        self.scroll_into_view_css(css_sel)
        element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
        try:
            element.click()
        except:  # noqa: E722
            self.driver.execute_script("arguments[0].click();", element)

    def click_by_link_text(self, link_text):
        for i in range(3):
            try:
                self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, link_text)))
                self.driver.find_element(By.LINK_TEXT, link_text).click()
                break
            except:  # noqa: E722
                if i == 2:
                    raise
                else:
                    time.sleep(1)
