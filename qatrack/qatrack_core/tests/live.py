from contextlib import contextmanager
from functools import wraps
import time

from django.conf import settings
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.servers.basehttp import WSGIServer
from django.test.testcases import LiveServerThread, QuietWSGIRequestHandler
import pytest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
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
        use_chrome = getattr(settings, 'SELENIUM_USE_CHROME', False)

        if use_virtual_display:
            # Make sure xvfb is installed
            from pyvirtualdisplay import Display
            cls.display = Display(visible=0, size=(1920, 1080))
            cls.display.start()
        else:
            cls.display = None

        if use_chrome:
            chrome_driver_path = getattr(settings, 'SELENIUM_CHROME_PATH', '')
            cls.driver = webdriver.Chrome(executable_path=chrome_driver_path)
        else:
            ff_profile = FirefoxProfile()
            cls.driver = webdriver.Firefox(ff_profile)

        orig_find_element = cls.driver.find_element

        @retry_if_exception(WebDriverException, 2, sleep_time=1)
        def WebElement_find_element(*args, **kwargs):
            """Monky patch find element to allow retries"""
            return orig_find_element(*args, **kwargs)
        cls.driver.find_element = WebElement_find_element

        cls.driver.set_page_load_timeout(2)
        cls.driver.implicitly_wait(2)

        cls.maximize()
        cls.wait = WebDriverWait(cls.driver, 2)

        super(SeleniumTests, cls).setUpClass()

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
        super(SeleniumTests, cls).tearDownClass()

    @contextmanager
    def wait_for_page_load(self, timeout=2):
        old_page = self.driver.find_element_by_tag_name('html')
        yield
        WebDriverWait(self.driver, timeout).until(
            staleness_of(old_page)
        )

    @retry_if_exception(Exception, 2, sleep_time=1)
    def open(self, url):
        with self.wait_for_page_load():
            self.driver.execute_script(
                "window.location.href='%s%s'" % (self.live_server_url, url)
            )

    def wait_for_success(self):
        self.wait.until(
            e_c.presence_of_element_located((By.XPATH, '//ul[@class = "messagelist"]/li[@class = "success"]'))
        )

    def scroll_into_view(self, el_id):
        self.wait.until(e_c.presence_of_element_located((By.ID, el_id)))
        actions = ActionChains(self.driver)
        element = self.driver.find_element_by_id(el_id)
        actions.move_to_element(element)
        time.sleep(1)
        actions.perform()
        self.driver.execute_script("window.scrollTo(0, -200);")

    def scroll_into_view_css(self, css_sel):
        self.wait.until(e_c.presence_of_element_located((By.CSS_SELECTOR, css_sel)))
        actions = ActionChains(self.driver)
        element = self.driver.find_element_by_css_selector(css_sel)
        actions.move_to_element(element)
        time.sleep(1)
        actions.perform()
        self.driver.execute_script("window.scrollTo(0, -200);")

    def select_by_index(self, el_id, index):

        self.scroll_into_view(el_id)
        try:
            select = Select(self.driver.find_element_by_id(el_id))
            select.select_by_index(1)
        except:  # noqa: E722
            # select2?
            sel2 = self.driver.find_element_by_id("select2-%s-container" % el_id)
            sel2.click()
            els = self.driver.find_elements_by_class_name("select2-results__option")
            els[index].click()

    def select_by_text(self, el_id, text):

        self.scroll_into_view(el_id)
        try:
            select = Select(self.driver.find_element_by_id(el_id))
            select.select_by_visible_text(text)
        except:  # noqa: E722

            sel2 = self.driver.find_element_by_id("select2-%s-container" % el_id)
            sel2.click()

            els = self.driver.find_elements_by_class_name("select2-results__option")
            for el in els:
                if el.text == text:
                    el.click()
                    break

    def select_by_value(self, el_id, val):

        self.scroll_into_view(el_id)
        try:
            select = Select(self.driver.find_element_by_id(el_id))
            select.select_by_value(val)
        except:  # noqa: E722

            sel2 = self.driver.find_element_by_id("select2-%s-container" % el_id)
            sel2.click()

            els = self.driver.find_elements_by_class_name("select2-results__option")
            for el in els:
                if el.get_attribute('value') == val:
                    el.click()
                    break

    def send_keys(self, el_id, text):
        for i in range(3):
            try:
                self.scroll_into_view(el_id)
                self.driver.find_element_by_id(el_id).send_keys(text)
                break
            except:  # noqa: E722
                if i == 2:
                    raise
                else:
                    time.sleep(1)

    def click(self, el_id):
        self.scroll_into_view(el_id)
        element = self.driver.find_element_by_id(el_id)
        self.driver.execute_script("arguments[0].click();", element)

    def click_by_css_selector(self, css_sel):
        self.scroll_into_view_css(css_sel)
        element = self.driver.find_element_by_css_selector(css_sel)
        try:
            element.click()
        except:
            self.driver.execute_script("arguments[0].click();", element)
