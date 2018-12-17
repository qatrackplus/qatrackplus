from contextlib import contextmanager
from functools import wraps
import time

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import TestCase
from django.utils import timezone
import pytest
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as e_c
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from qatrack.qa import models
from qatrack.service_log.tests import utils as sl_utils

from . import utils

objects = {
    'Group': {
        'name': 'testGroup',
    },
    'Category': {
        'name': 'testCategory',
        'slug': 'testCategory',
        'description': 'test test test test'
    },
    'Tests': [
        {
            'test_type': models.SIMPLE,
            'name': 'simple',
            'choices': None,
            'constant_value': None,
            'procedure': None
        },
        {
            'test_type': models.BOOLEAN,
            'name': 'boolean',
            'choices': None,
            'constant_value': None,
            'procedure': None
        },
        {
            'test_type': models.MULTIPLE_CHOICE,
            'name': 'multchoice',
            'choices': '1,2,3,4,5',
            'constant_value': None,
            'procedure': None
        },
        {
            'test_type': models.CONSTANT,
            'name': 'constant',
            'choices': None,
            'constant_value': '23.23',
            'procedure': None
        },
        {
            'test_type': models.COMPOSITE,
            'name': 'composite',
            'choices': None,
            'constant_value': None,
            'procedure': 'result = constant * simpleNumeric'
        },
        {
            'test_type': models.STRING,
            'name': 'string',
            'choices': None,
            'constant_value': None,
            'procedure': None
        },
        {
            'test_type': models.STRING_COMPOSITE,
            'name': 'scomposite',
            'choices': None,
            'constant_value': None,
            'procedure': 'result = string + " composite"'
        },
        {
            'test_type': models.UPLOAD,
            'name': 'upload',
            'choices': None,
            'constant_value': None,
            'procedure': 'result = FILE[0]'
        }
    ],
    'TestList': {
        'name': 'TestTestList'
    },
    'Modality': {
        'name': 'TestModality'
    },
    'UnitType': {
        'name': 'TestModality',
        'vendor': 'TestVendor'
    },
    'Unit': {
        'name': 'TestUnit',
        'number': '1',
        'date_acceptance': timezone.now().strftime('%Y-%m-%d')
    },
    'Frequency': {
        'name': 'TestFrequency',
        'nominal_interval': '2',
        'due_interval': '3',
        'window_end': '4'
    },
    'UnitTestCollection': {

    },
    'absoluteTolerance': {
        'act_low': '-2',
        'tol_low': '-1',
        'tol_high': '1',
        'act_high': '2'
    },
    'percentTolerance': {
        'act_low': '-5',
        'tol_low': '-1',
        'tol_high': '1',
        'act_high': '5'
    },
    'multiChoiceTolerance': {
        'mc_pass_choices': '3',
        'mc_tol_choices': '2,4'
    },
    'refTols': {
        'multipleChoice': {},
        'simpleNumeric': {
            'reference_value': '0'
        },
        'composite': {
            'reference_value': '23.23'
        }
    },
    'statuses': {
        'testStatus': {
            'default': True,
            'requiresApproval': True
        },
        'testApprovalStatus': {
            'dfault': False,
            'requiresApproval': False
        }
    },

}


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
                except:
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
WebElement.click = WebElement_click


orig_send_keys = WebElement.send_keys
@retry_if_exception(WebDriverException, 5, sleep_time=1)
def WebElement_send_keys(self, keys):
    """Monky patch send_keys to ensure element is in view"""
    self.parent.execute_script("arguments[0].scrollIntoView();", self)
    return orig_send_keys(self, keys)
WebElement.send_keys = WebElement_send_keys


@pytest.mark.selenium
class SeleniumTests(TestCase, StaticLiveServerTestCase):

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

        @retry_if_exception(WebDriverException, 5, sleep_time=1)
        def WebElement_find_element(*args, **kwargs):
            """Monky patch find element to allow retries"""
            return orig_find_element(*args, **kwargs)
        cls.driver.find_element = WebElement_find_element

        cls.driver.set_page_load_timeout(5)
        cls.driver.implicitly_wait(5)

        cls.maximize()
        cls.wait = WebDriverWait(cls.driver, 5)

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

    def load_main(self):
        self.open("")
        self.wait.until(e_c.presence_of_element_located((By.CSS_SELECTOR, "head > title")))

    @contextmanager
    def wait_for_page_load(self, timeout=10):
        old_page = self.driver.find_element_by_tag_name('html')
        yield
        WebDriverWait(self.driver, timeout).until(
            staleness_of(old_page)
        )

    @retry_if_exception(Exception, 5, sleep_time=1)
    def open(self, url):
        with self.wait_for_page_load():
            self.driver.execute_script(
                "window.location.href='%s%s'" % (self.live_server_url, url)
            )

    def load_admin(self):
        self.open("/admin/")
        self.driver.find_element_by_id('id_username').send_keys(self.user.username)
        self.driver.find_element_by_id('id_password').send_keys(self.password)
        self.driver.find_element_by_css_selector('button').click()

        self.wait.until(e_c.presence_of_element_located((By.CSS_SELECTOR, "head > title")))

    def setUp(self):

        self.password = 'password'
        self.user = utils.create_user(pwd=self.password)

    def wait_for_success(self):
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//ul[@class = "messagelist"]/li[@class = "success"]')
            )
        )

    def test_admin_category(self):

        self.load_admin()
        self.driver.find_element_by_xpath('//a[@href="/admin/qa/category/"]').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD CATEGORY')))
        self.driver.find_element_by_link_text('ADD CATEGORY').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys(objects['Category']['name'])
        self.driver.find_element_by_id('id_slug').send_keys(objects['Category']['slug'])
        self.driver.find_element_by_id('id_description').send_keys(objects['Category']['description'])
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_tests(self):

        self.load_admin()

        if not utils.exists('qa', 'Category', 'name', objects['Category']['name']):
            utils.create_category(name=objects['Category']['name'], slug=objects['Category']['slug'], description=objects['Category']['description'])

        self.driver.find_element_by_link_text('Tests').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD TEST')))
        self.driver.find_element_by_link_text('ADD TEST').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        # for i in range(len(objects['Tests'])):

        for i in range(len(objects['Tests'])):
            # the_test = objects['Tests'][i]
            the_test = objects['Tests'][i]
            self.driver.find_element_by_id('id_name').send_keys(the_test['name'])
            self.driver.find_element_by_id('id_slug').send_keys(the_test['name'])
            Select(self.driver.find_element_by_id('id_category')).select_by_index(1)
            Select(self.driver.find_element_by_id('id_type')).select_by_value(the_test['name'])

            if the_test['choices']:
                self.driver.find_element_by_id('id_choices').send_keys('1,2,3,4,5')
            if the_test['constant_value']:
                self.driver.find_element_by_id('id_constant_value').send_keys('23.23')
            if the_test['procedure']:
                time.sleep(1)
                self.driver.find_element_by_css_selector('#calc-procedure-editor > textarea').send_keys(the_test['procedure'])
                self.driver.find_element_by_css_selector('.submit-row').click()

            # Firefox webdriver being weird with clicks. Had to use javascript here:
            if i + 1 == len(objects['Tests']):
                self.driver.execute_script("$('input[name=_save]').click();")
            else:
                self.driver.execute_script("$('input[name=_addanother]').click();")

            self.wait_for_success()

    def test_admin_testlist(self):

        self.load_admin()

        for i in range(len(objects['Tests'])):
            the_test = objects['Tests'][i]
            if not utils.exists('qa', 'Test', 'name', the_test['name']):
                utils.create_test(name=the_test['name'], test_type=the_test['test_type'], choices=the_test['choices'], procedure=the_test['procedure'], constant_value=the_test['constant_value'])

        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Test lists')))
        self.driver.find_element_by_link_text('Test lists').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD TEST LIST')))
        self.driver.find_element_by_link_text('ADD TEST LIST').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys(objects['TestList']['name'])
        self.driver.find_element_by_link_text('Add another Test List Membership').click()
        self.driver.find_element_by_link_text('Add another Test List Membership').click()
        self.driver.find_element_by_link_text('Add another Test List Membership').click()
        for i, pk in enumerate(models.Test.objects.values_list("pk", flat=True)):
            self.driver.find_element_by_id('id_testlistmembership_set-' + str(i) + '-test').send_keys(str(pk))
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_modality(self):

        self.load_admin()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Modalities')))
        self.driver.find_element_by_link_text('Modalities').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD MODALITY')))
        self.driver.find_element_by_link_text('ADD MODALITY').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys(objects['Modality']['name'])
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_unittype(self):

        self.load_admin()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Unit types')))
        self.driver.find_element_by_link_text('Unit types').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD UNIT TYPE')))
        self.driver.find_element_by_link_text('ADD UNIT TYPE').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys(objects['UnitType']['name'])
        self.driver.find_element_by_id('id_vendor').send_keys(objects['UnitType']['vendor'])
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_unit(self):

        if not utils.exists('units', 'UnitType', 'name', objects['UnitType']['name']):
            utils.create_unit_type(
                name=objects['UnitType']['name'], vendor=utils.create_vendor(objects['UnitType']['vendor'])
            )

        if not utils.exists('units', 'Modality', 'name', objects['Modality']['name']):
            utils.create_modality(name=objects['Modality']['name'])

        sl_utils.create_service_area()

        self.load_admin()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Units')))
        self.driver.find_elements_by_link_text('Units')[0].click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD UNIT')))
        self.driver.find_element_by_link_text('ADD UNIT').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys(objects['Unit']['name'])
        self.driver.find_element_by_id('id_number').send_keys(objects['Unit']['number'])
        self.driver.find_element_by_id('id_date_acceptance').send_keys(objects['Unit']['date_acceptance'])
        if settings.USE_SERVICE_LOG:
            self.driver.find_element_by_css_selector('#id_service_areas_add_all_link').click()
        Select(self.driver.find_element_by_id("id_type")).select_by_index(1)
        # self.driver.find_element_by_id('id_modalities_add_all_link').click()
        # self.driver.find_element_by_id('id_hours_monday').send_keys('800')
        # self.driver.find_element_by_id('id_hours_tuesday').send_keys('800')
        # self.driver.find_element_by_id('id_hours_wednesday').send_keys('800')
        # self.driver.find_element_by_id('id_hours_thursday').send_keys('800')
        # self.driver.find_element_by_id('id_hours_friday').send_keys('800')
        # self.driver.find_element_by_id('id_hours_saturday').send_keys('800')
        # self.driver.find_element_by_id('id_hours_sunday').send_keys('800')
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_frequency(self):

        self.load_admin()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Frequencies')))
        self.driver.find_element_by_link_text('Frequencies').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD FREQUENCY')))
        self.driver.find_element_by_link_text('ADD FREQUENCY').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys(objects['Frequency']['name'])
        self.driver.find_element_by_class_name("recurrence-label").click()
        self.driver.find_elements_by_css_selector(".weekly td")[0].click()
        self.driver.find_elements_by_css_selector(".weekly td")[2].click()
        self.driver.find_elements_by_css_selector(".weekly td")[4].click()
        self.driver.find_element_by_id('id_window_end').send_keys(objects['Frequency']['window_end'])
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()
        assert models.Frequency.objects.get(name=objects['Frequency']['name']).nominal_interval < 3

    def test_admin_unittestcollection(self):

        if not utils.exists('auth', 'Group', 'name', objects['Group']['name']):
            utils.create_group(name=objects['Group']['name'])

        if not utils.exists('units', 'Unit', 'name', objects['Modality']['name']):
            utils.create_unit(name=objects['Modality']['name'], number=objects['Unit']['number'])

        if not utils.exists('qa', 'Frequency', 'name', objects['Frequency']['name']):
            utils.create_frequency(name=objects['Frequency']['name'])

        if not utils.exists('qa', 'TestList', 'name', objects['TestList']['name']):
            utils.create_test_list(name=objects['TestList']['name'])

        self.load_admin()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Assign Test Lists to Units')))
        self.driver.find_element_by_link_text('Assign Test Lists to Units').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD UNIT TEST COLLECTION')))
        self.driver.find_element_by_link_text('ADD UNIT TEST COLLECTION').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_unit')))

        Select(self.driver.find_element_by_id("id_unit")).select_by_index(1)
        Select(self.driver.find_element_by_id("id_frequency")).select_by_index(1)
        Select(self.driver.find_element_by_id("id_assigned_to")).select_by_index(1)
        Select(self.driver.find_element_by_id("id_content_type")).select_by_index(1)
        self.driver.find_element_by_css_selector('#id_visible_to_from > option:nth-child(1)').click()
        self.driver.find_element_by_css_selector('#id_visible_to_add_link').click()

        time.sleep(2)

        self.driver.find_element_by_id('select2-generic_object_id-container').click()
        self.driver.find_element_by_id('select2-generic_object_id-container').click()
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_tolerances(self):

        # Add absolute tolerance
        self.load_admin()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Tolerances')))
        self.driver.find_element_by_link_text('Tolerances').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD TOLERANCE')))
        self.driver.find_element_by_link_text('ADD TOLERANCE').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_type')))
        Select(self.driver.find_element_by_id("id_type")).select_by_index(1)
        self.driver.find_element_by_id('id_act_low').send_keys(objects['absoluteTolerance']['act_low'])
        self.driver.find_element_by_id('id_tol_low').send_keys(objects['absoluteTolerance']['tol_low'])
        self.driver.find_element_by_id('id_tol_high').send_keys(objects['absoluteTolerance']['tol_high'])
        self.driver.find_element_by_id('id_act_high').send_keys(objects['absoluteTolerance']['act_high'])
        self.driver.find_element_by_name('_addanother').click()
        self.wait_for_success()

        # Add percentage tolerance
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_type')))
        Select(self.driver.find_element_by_id("id_type")).select_by_index(1)
        self.driver.find_element_by_id('id_act_low').send_keys(objects['percentTolerance']['act_low'])
        self.driver.find_element_by_id('id_tol_low').send_keys(objects['percentTolerance']['tol_low'])
        self.driver.find_element_by_id('id_tol_high').send_keys(objects['percentTolerance']['tol_high'])
        self.driver.find_element_by_id('id_act_high').send_keys(objects['percentTolerance']['act_high'])
        self.driver.find_element_by_name('_addanother').click()
        self.wait_for_success()

        # Add multi tolerance
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_type')))
        Select(self.driver.find_element_by_id("id_type")).select_by_index(3)
        self.driver.find_element_by_id('id_mc_pass_choices').send_keys(objects['multiChoiceTolerance']['mc_pass_choices'])
        self.driver.find_element_by_id('id_mc_tol_choices').send_keys(objects['multiChoiceTolerance']['mc_tol_choices'])
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_set_ref_tols(self):

        utils.create_tolerance(tol_type=models.MULTIPLE_CHOICE, mc_pass_choices="a,b")

        utils.create_tolerance()

        for the_test in objects['Tests']:

            if the_test['test_type'] == models.MULTIPLE_CHOICE:
                if not utils.exists('qa', 'Test', 'name', the_test['name']):
                    mult_test = utils.create_test(test_type=models.MULTIPLE_CHOICE, choices=the_test['choices'], name=the_test['name'])
            elif the_test['test_type'] == models.SIMPLE:
                if not utils.exists('qa', 'Test', 'name', the_test['name']):
                    simp_test = utils.create_test(test_type=models.SIMPLE, name=the_test['name'])
            elif the_test['test_type'] == models.COMPOSITE:
                if not utils.exists('qa', 'Test', 'name', the_test['name']):
                    comp_test = utils.create_test(test_type=models.COMPOSITE, name=the_test['name'])

        if not utils.exists('qa', 'TestList', 'name', objects['TestList']['name']):
            test_list = utils.create_test_list(objects['TestList']['name'])
            utils.create_test_list_membership(test_list=test_list, test=mult_test)
            utils.create_test_list_membership(test_list=test_list, test=simp_test)
            utils.create_test_list_membership(test_list=test_list, test=comp_test)

        utils.create_unit_test_collection(test_collection=test_list)

        self.load_admin()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Set References & Tolerances')))
        self.driver.find_element_by_link_text('Set References & Tolerances').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, mult_test.name)))
        self.driver.find_element_by_link_text(mult_test.name).click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_tolerance')))
        Select(self.driver.find_element_by_id("id_tolerance")).select_by_index(1)
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

        self.driver.find_element_by_link_text('simple').click()
        Select(self.driver.find_element_by_id("id_tolerance")).select_by_index(1)
        self.driver.find_element_by_id('id_reference_value').send_keys('0')
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

        self.driver.find_element_by_link_text('composite').click()
        Select(self.driver.find_element_by_id("id_tolerance")).select_by_index(1)
        self.driver.find_element_by_id('id_reference_value').send_keys('23.23')
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_statuses(self):

        self.load_admin()
        self.wait.until(e_c.presence_of_element_located((By.XPATH, "//a[contains(@href,'testinstancestatus')]")))
        self.driver.find_element_by_xpath("//a[contains(@href,'testinstancestatus')]").click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'ADD TEST INSTANCE STATUS')))
        self.driver.find_element_by_link_text('ADD TEST INSTANCE STATUS').click()
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys('testStatus')
        self.driver.find_element_by_id('id_is_default').click()
        self.driver.find_element_by_name('_addanother').click()
        self.wait_for_success()

        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys('testApprovalStatus')
        self.driver.find_element_by_id('id_requires_review').click()
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def rest(self):

        self.load_main()

        # Perform test
        self.driver.find_element_by_link_text('Choose a Unit to perform QC for').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'TestUnit')))
        self.driver.find_element_by_link_text('TestUnit').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Perform')))
        self.driver.find_element_by_link_text('Perform').click()

        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_form-0-value')))
        basic = self.driver.find_element_by_id('id_form-0-value')
        boolean = self.driver.find_element_by_name('form-1-value')
        basic.send_keys('3')
        boolean.click()
        self.wait.until(e_c.presence_of_element_located((By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[1]/td[5][contains(text(), "ACT(3.00)")]')))
        # self.assertTrue(self.driver.find_element_by_xpath('//*[@id="perform-qa-table"]/tbody/tr[1]/td[5]').text == 'ACT(3.00)')
        basic.send_keys(Keys.BACKSPACE, '2')
        boolean.click()
        self.wait.until(e_c.presence_of_element_located((By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[1]/td[5][contains(text(), "TOL(2.00)")]')))
        # self.assertTrue(self.driver.find_element_by_xpath('//*[@id="perform-qa-table"]/tbody/tr[1]/td[5]').text == 'TOL(2.00)')
        basic.send_keys(Keys.BACKSPACE, '1')
        boolean.click()
        self.wait.until(e_c.presence_of_element_located((By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[1]/td[5][contains(text(), "OK(1.00)")]')))
        # self.assertTrue(self.driver.find_element_by_xpath('//*[@id="perform-qa-table"]/tbody/tr[1]/td[5]').text == 'OK(1.00)')
        self.wait.until(e_c.presence_of_element_located((By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[13]/td[5][contains(text(), "OK(0.0%)")]')))
        # self.assertTrue(self.driver.find_element_by_xpath('//*[@id="perform-qa-table"]/tbody/tr[13]/td[5]').text == 'OK(0.0%)')
        basic.send_keys(Keys.BACKSPACE, '1.06')
        boolean.click()
        self.wait.until(e_c.presence_of_element_located((By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[13]/td[5][contains(text(), "ACT(6.0%)")]')))
        # self.assertTrue(self.driver.find_element_by_xpath('//*[@id="perform-qa-table"]/tbody/tr[13]/td[5]').text == 'ACT(6.0%)')
        basic.send_keys(Keys.BACKSPACE, '5')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[13]/td[5][contains(text(), "TOL(5.0%)")]')
            )
        )
        # self.assertTrue(self.driver.find_element_by_xpath('//*[@id="perform-qa-table"]/tbody/tr[13]/td[5]').text == 'TOL(5.0%)')
        basic.send_keys(Keys.BACKSPACE, Keys.BACKSPACE, Keys.BACKSPACE)
        boolean.click()
        # time.sleep(1)

        multi = self.driver.find_element_by_id('id_form-2-string_value')
        multi.click()
        multi.send_keys(Keys.ARROW_DOWN, Keys.ENTER)
        self.assertTrue(
            self.driver.find_element_by_xpath('//*[@id="perform-qa-table"]/tbody/tr[7]/td[5]').text == 'ACT'
        )
        multi.click()
        multi.send_keys(Keys.ARROW_DOWN, Keys.ENTER)
        self.assertTrue(
            self.driver.find_element_by_xpath('//*[@id="perform-qa-table"]/tbody/tr[7]/td[5]').text == 'TOL'
        )
        multi.click()
        multi.send_keys(Keys.ARROW_DOWN, Keys.ENTER)
        self.assertTrue(self.driver.find_element_by_xpath('//*[@id="perform-qa-table"]/tbody/tr[7]/td[5]').text == 'OK')

        self.driver.find_element_by_id('id_form-5-string_value').send_keys('a string')
        boolean.click()
        self.wait.until(
            e_c.text_to_be_present_in_element_value((By.ID, 'id_form-6-string_value'), 'a string composite')
        )

        self.driver.find_element_by_id('id_form-7-skipped').click()

        self.driver.find_element_by_id('submit-qa').click()

        self.wait.until(e_c.presence_of_element_located((By.XPATH, '//div[contains(text(), "Showing 1 to 1")]')))
        self.driver.find_element_by_partial_link_text('Review Data').click()
        self.driver.find_element_by_partial_link_text('Unreviewed Visible To Your Groups').click()
        self.wait.until(e_c.presence_of_element_located((By.LINK_TEXT, 'Review')))
        self.driver.find_element_by_link_text('Review').click()

        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_testinstance_set-0-status')))
        self.driver.find_element_by_id('bulk-status').click()
        self.driver.find_element_by_id('bulk-status').send_keys(Keys.ARROW_DOWN, Keys.ARROW_DOWN, Keys.ENTER)

        self.driver.find_element_by_xpath('//button[@type = "submit"]').click()

        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//td[contains(text(), "No data available in table")]')
            )
        )
