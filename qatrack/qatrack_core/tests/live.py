import shutil
import time
from contextlib import contextmanager
from functools import wraps

import pytest
from django.conf import settings
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
    self.parent.execute_script("arguments[0].scrollIntoView({block: 'center'});", self)
    return self._execute(Command.CLICK_ELEMENT)


WebElement.click = WebElement_click  # noqa: E305

orig_send_keys = WebElement.send_keys


@retry_if_exception(WebDriverException, 5, sleep_time=1)  # noqa: E302
def WebElement_send_keys(self, keys):
    """Monky patch send_keys to ensure element is in view"""
    self.parent.execute_script("arguments[0].scrollIntoView({block: 'center'});", self)
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

    @contextmanager
    def wait_for_page_load(self, timeout=2):
        old_page = self.driver.find_element(By.TAG_NAME, 'html')
        yield
        WebDriverWait(self.driver, timeout).until(staleness_of(old_page))

    @retry_if_exception(Exception, 2, sleep_time=1)
    def open(self, url):
        with self.wait_for_page_load():
            self.driver.execute_script("window.location.href='%s%s'" % (self.live_server_url, url))

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
            self.driver.execute_script("window.scrollBy(0, -200);")
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
            self.driver.execute_script("window.scrollBy(0, -200);")
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
            select = Select(self.driver.find_element(By.ID, el_id))
            select.select_by_index(index)

    def select_by_text(self, el_id, text):

        self.scroll_into_view(el_id)
        try:
            select = Select(self.driver.find_element(By.ID, el_id))
            select.select_by_visible_text(text)
        except:  # noqa: E722

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
            select = Select(self.driver.find_element(By.ID, el_id))
            select.select_by_value(val)
        except:  # noqa: E722

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
