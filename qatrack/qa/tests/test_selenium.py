import time

import pytest
from django.conf import settings
from django.contrib.auth.models import Permission
from django.db import transaction
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format, get_format
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as e_c

from qatrack.accounts.tests.utils import create_group, create_user
from qatrack.qa import models
from qatrack.qa.tests import utils
from qatrack.qatrack_core.dates import format_as_date
from qatrack.qatrack_core.tests.live import SeleniumTests
from qatrack.service_log.tests import utils as sl_utils

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
        }, {
            'test_type': models.BOOLEAN,
            'name': 'boolean',
            'choices': None,
            'constant_value': None,
            'procedure': None
        }, {
            'test_type': models.MULTIPLE_CHOICE,
            'name': 'multchoice',
            'choices': '1,2,3,4,5',
            'constant_value': None,
            'procedure': None
        }, {
            'test_type': models.CONSTANT,
            'name': 'constant',
            'choices': None,
            'constant_value': '23.23',
            'procedure': None
        }, {
            'test_type': models.COMPOSITE,
            'name': 'composite',
            'choices': None,
            'constant_value': None,
            'procedure': 'result = constant * simpleNumeric'
        }, {
            'test_type': models.STRING,
            'name': 'string',
            'choices': None,
            'constant_value': None,
            'procedure': None
        }, {
            'test_type': models.STRING_COMPOSITE,
            'name': 'scomposite',
            'choices': None,
            'constant_value': None,
            'procedure': 'result = string + " composite"'
        }, {
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
        'date_acceptance': format_as_date(timezone.now())
    },
    'Frequency': {
        'name': 'TestFrequency',
        'nominal_interval': '2',
        'due_interval': '3',
        'window_end': '4'
    },
    'UnitTestCollection': {},
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
}  # yapf: disable


class BaseQATests(SeleniumTests, TransactionTestCase):

    def setUp(self):
        with transaction.atomic():
            self.password = 'password'
            self.user = create_user(pwd=self.password)

    def login(self):
        self.open("/accounts/login/")
        self.send_keys("id_username", self.user.username)
        self.send_keys("id_password", self.password)
        self.driver.find_element(By.CSS_SELECTOR, 'button').click()

        # The logout link is inside {% if user.is_authenticated %}, so its
        # presence proves both that the POST was handled and that the redirect
        # rendered. Waiting on something every page has would be satisfied
        # immediately, with the login page still on screen.
        self.wait.until(
            e_c.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="logout"]')),
            "the logged-in navbar (a logout link) after submitting the login form",
        )

    def load_main(self):
        self.login()
        self.open("")

    def load_admin(self):
        self.open("/admin/")
        self.send_keys("id_username", self.user.username)
        self.send_keys("id_password", self.password)
        self.driver.find_element(By.CSS_SELECTOR, 'button').click()

        # #user-tools is the admin header's account block, rendered only once
        # authenticated. The admin has no logout href to wait on as login()
        # does - Django 4.1 made admin logout a POST form.
        self.wait.until(
            e_c.presence_of_element_located((By.CSS_SELECTOR, '#user-tools')),
            "the Django admin chrome (#user-tools) after loading the admin index",
        )


@pytest.mark.selenium
class LiveQATests(BaseQATests):

    def setUp(self):

        super().setUp()

    def test_driver_can_screenshot(self):
        """The browser half of the failure-screenshot feature.

        tearDown captures the page on every test and swallows
        WebDriverException, because a screenshot must never replace a real
        test result - which also means a driver that cannot screenshot at all
        would go unnoticed. This asserts the capability that every failure
        screenshot depends on. The hook that decides whether to keep the
        image is covered without a browser in
        qatrack/qatrack_core/tests/test_screenshot_hook.py.
        """
        png = self.driver.get_screenshot_as_png()
        assert png[:8] == b'\x89PNG\r\n\x1a\n', png[:16]
        # A blank page still encodes to a valid PNG, so check it has content:
        # the viewport is 1920x1080 and a rendered page runs orders of
        # magnitude above an empty one.
        assert len(png) > 5000, len(png)

    def test_browser_timezone_matches_server(self):
        """The browser and the test server must agree on what day it is.

        Several tests fill a date picker from the browser and then assert
        against `timezone.localtime(now)` on the server. When the two zones
        differ the picker chooses one date and the assertion expects another,
        so the tests fail for the hours either side of midnight in one zone
        but not the other - and pass the rest of the day, which is what makes
        it look like flakiness. On a UTC-6 workstation against a Toronto
        server that window is 22:00-00:00 local, every night.

        setUpClass passes TZ to the driver's Service environment to remove the
        difference. This asserts it took effect, because the failure it
        prevents is invisible outside that window.
        """
        browser_tz = self.driver.execute_script(
            "return Intl.DateTimeFormat().resolvedOptions().timeZone"
        )
        assert browser_tz == settings.TIME_ZONE, (
            "browser is on %s, server on %s - date-sensitive tests will "
            "disagree around midnight" % (browser_tz, settings.TIME_ZONE)
        )

        browser_date = self.driver.execute_script(
            "var d = new Date();"
            "return [d.getFullYear(), d.getMonth() + 1, d.getDate()];"
        )
        server_date = timezone.localtime(timezone.now()).date()
        assert tuple(browser_date) == (server_date.year, server_date.month, server_date.day)

    def test_admin_category(self):

        self.load_admin()
        self.driver.find_element(By.XPATH, '//a[@href="/admin/qa/category/"]').click()
        self.click_by_link_text("ADD CATEGORY")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')), "the category admin form to render")
        self.driver.find_element(By.ID, 'id_name').send_keys(objects['Category']['name'])
        self.driver.find_element(By.ID, 'id_slug').send_keys(objects['Category']['slug'])
        self.driver.find_element(By.ID, 'id_description').send_keys(objects['Category']['description'])
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

    def test_admin_tests(self):

        self.load_admin()

        if not utils.exists('qa', 'Category', 'name', objects['Category']['name']):
            utils.create_category(
                name=objects['Category']['name'],
                slug=objects['Category']['slug'],
                description=objects['Category']['description'],
            )

        self.driver.find_element(By.LINK_TEXT, 'Tests').click()
        self.click_by_link_text("ADD TEST")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')), "the test admin form to render")
        # for i in range(len(objects['Tests'])):

        for i in range(len(objects['Tests'])):
            # the_test = objects['Tests'][i]
            the_test = objects['Tests'][i]
            self.send_keys('id_name', the_test['name'])
            self.send_keys('id_slug', the_test['name'])
            self.select_by_index('id_category', 1)
            self.select_by_value('id_type', the_test['name'])
            # NOT wait_for_ajax(): choosing the test type re-renders the
            # type-dependent fields client side with no request in flight, so
            # an AJAX wait returns immediately and the fields below are filled
            # before they exist.
            self.wait_for_ajax()
            time.sleep(0.1)

            if the_test['choices']:
                self.send_keys('id_choices', '1,2,3,4,5')
            if the_test['constant_value']:
                self.send_keys('id_constant_value', '23.23')
            if the_test['procedure']:
                time.sleep(1)
                self.driver.find_element(By.CSS_SELECTOR, '#calc-procedure-editor > textarea').send_keys(
                    the_test['procedure'],
                )
                self.driver.find_element(By.CSS_SELECTOR, '.submit-row').click()

            # Firefox webdriver being weird with clicks. Had to use javascript here:
            if i + 1 == len(objects['Tests']):
                self.execute_jquery_script("$('input[name=_save]').click();")
            else:
                self.execute_jquery_script("$('input[name=_addanother]').click();")

            for i in range(3):
                try:
                    self.wait_for_success()
                    break
                except:  # noqa: E722
                    if i == 2:
                        raise
                    else:
                        time.sleep(1)

    def test_admin_testlist(self):

        self.load_admin()

        for i in range(len(objects['Tests'])):
            the_test = objects['Tests'][i]
            if not utils.exists('qa', 'Test', 'name', the_test['name']):
                utils.create_test(
                    name=the_test['name'],
                    test_type=the_test['test_type'],
                    choices=the_test['choices'],
                    procedure=the_test['procedure'],
                    constant_value=the_test['constant_value'],
                )

        self.click_by_link_text("Test Lists")
        self.click_by_link_text("ADD TEST LIST")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')), "the test list admin form to render")
        self.driver.find_element(By.ID, 'id_name').send_keys(objects['TestList']['name'])
        self.driver.find_element(By.ID, 'id_slug').send_keys(objects['TestList']['name'].lower())
        self.driver.find_element(By.LINK_TEXT, 'Add another Test List Membership').click()
        self.driver.find_element(By.LINK_TEXT, 'Add another Test List Membership').click()
        self.driver.find_element(By.LINK_TEXT, 'Add another Test List Membership').click()
        for i, pk in enumerate(models.Test.objects.values_list("pk", flat=True)):
            self.driver.find_element(By.ID, 'id_testlistmembership_set-' + str(i) + '-test').send_keys(str(pk))
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

    def test_admin_modality(self):

        self.load_admin()
        self.click_by_link_text("Treatment and Imaging Modalities")
        self.click_by_link_text("ADD TREATMENT AND IMAGING MODALITY")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')), "the modality admin form to render")
        self.driver.find_element(By.ID, 'id_name').send_keys(objects['Modality']['name'])
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

    def test_admin_unittype(self):

        self.load_admin()
        self.click_by_link_text("Unit Types")
        self.click_by_link_text("ADD UNIT TYPE")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')), "the unit type admin form to render")
        self.driver.find_element(By.ID, 'id_name').send_keys(objects['UnitType']['name'])
        self.driver.find_element(By.ID, 'id_vendor').send_keys(objects['UnitType']['vendor'])
        self.driver.find_element(By.NAME, '_save').click()
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
        self.click_by_link_text("Units")
        self.click_by_link_text("ADD UNIT")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')), "the unit admin form to render")
        self.driver.find_element(By.ID, 'id_name').send_keys(objects['Unit']['name'])
        self.driver.find_element(By.ID, 'id_number').send_keys(objects['Unit']['number'])
        self.driver.find_element(By.ID, 'id_date_acceptance').send_keys(objects['Unit']['date_acceptance'])
        self.driver.find_element(By.CSS_SELECTOR, '#id_service_areas_add_all_link').click()
        self.select_by_index("id_type", 1)
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

    def test_admin_frequency(self):

        self.load_admin()
        self.click_by_link_text("Frequencies")
        self.click_by_link_text("ADD FREQUENCY")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')), "the frequency admin form to render")
        self.driver.find_element(By.ID, 'id_name').send_keys(objects['Frequency']['name'])
        self.driver.find_element(By.CLASS_NAME, "recurrence-label").click()
        cells = self.wait_for_elements(By.CSS_SELECTOR, ".weekly td", minimum=5)
        cells[0].click()
        cells[2].click()
        cells[4].click()
        self.driver.find_element(By.ID, 'id_window_end').send_keys(objects['Frequency']['window_end'])
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()
        assert models.Frequency.objects.get(name=objects['Frequency']['name']).nominal_interval < 3

    def test_admin_unittestcollection(self):

        if not utils.exists('auth', 'Group', 'name', objects['Group']['name']):
            create_group(name=objects['Group']['name'])

        if not utils.exists('units', 'Unit', 'name', objects['Modality']['name']):
            utils.create_unit(name=objects['Modality']['name'], number=objects['Unit']['number'])

        if not utils.exists('qa', 'Frequency', 'name', objects['Frequency']['name']):
            utils.create_frequency(name=objects['Frequency']['name'])

        if not utils.exists('qa', 'TestList', 'name', objects['TestList']['name']):
            utils.create_test_list(name=objects['TestList']['name'])

        self.load_admin()
        self.click_by_link_text("Assign Test Lists to Units")
        self.click_by_link_text('ADD UNIT TEST COLLECTION')
        self.wait.until(
            e_c.presence_of_element_located((By.ID, 'id_unit')),
            "the unit test collection admin form to render",
        )

        self.select_by_index("id_unit", -1)
        self.wait_for_ajax()
        self.select_by_index("id_frequency", -1)
        self.select_by_index("id_assigned_to", 0)
        self.select_by_index("id_content_type", 1)
        self.driver.find_element(By.CSS_SELECTOR, '#id_visible_to_from > option:nth-child(1)').click()
        self.driver.find_element(By.CSS_SELECTOR, '#id_visible_to_add_link').click()

        self.wait_for_ajax()

        self.driver.find_element(By.ID, 'select2-generic_object_id-container').click()
        self.driver.find_element(By.ID, 'select2-generic_object_id-container').click()
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

    def test_admin_tolerances(self):

        # Add absolute tolerance
        self.load_admin()
        self.click_by_link_text('Tolerances')
        self.click_by_link_text('ADD TOLERANCE')
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_type')), "the tolerance admin form to render")
        self.select_by_index("id_type", 1)
        self.driver.find_element(By.ID, 'id_act_low').send_keys(objects['absoluteTolerance']['act_low'])
        self.driver.find_element(By.ID, 'id_tol_low').send_keys(objects['absoluteTolerance']['tol_low'])
        self.driver.find_element(By.ID, 'id_tol_high').send_keys(objects['absoluteTolerance']['tol_high'])
        self.driver.find_element(By.ID, 'id_act_high').send_keys(objects['absoluteTolerance']['act_high'])
        self.driver.find_element(By.NAME, '_addanother').click()
        self.wait_for_success()

        # Add percentage tolerance
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_type')), "the tolerance admin form to render")
        self.select_by_index("id_type", 1)
        self.driver.find_element(By.ID, 'id_act_low').send_keys(objects['percentTolerance']['act_low'])
        self.driver.find_element(By.ID, 'id_tol_low').send_keys(objects['percentTolerance']['tol_low'])
        self.driver.find_element(By.ID, 'id_tol_high').send_keys(objects['percentTolerance']['tol_high'])
        self.driver.find_element(By.ID, 'id_act_high').send_keys(objects['percentTolerance']['act_high'])
        self.driver.find_element(By.NAME, '_addanother').click()
        self.wait_for_success()

        # Add multi tolerance
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_type')), "the tolerance admin form to render")
        self.select_by_index("id_type", 3)
        self.driver.find_element(By.ID,
                                 'id_mc_pass_choices').send_keys(objects['multiChoiceTolerance']['mc_pass_choices'])
        self.driver.find_element(By.ID,
                                 'id_mc_tol_choices').send_keys(objects['multiChoiceTolerance']['mc_tol_choices'])
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

    def test_admin_set_ref_tols(self):

        utils.create_tolerance(tol_type=models.MULTIPLE_CHOICE, mc_pass_choices="a,b")

        utils.create_tolerance()

        for the_test in objects['Tests']:

            if the_test['test_type'] == models.MULTIPLE_CHOICE:
                if not utils.exists('qa', 'Test', 'name', the_test['name']):
                    mult_test = utils.create_test(
                        test_type=models.MULTIPLE_CHOICE, choices=the_test['choices'], name=the_test['name']
                    )
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
        self.click_by_link_text('Set References & Tolerances')
        self.click_by_link_text(mult_test.name)
        self.wait.until(
            e_c.presence_of_element_located((By.ID, 'id_tolerance')),
            "the reference/tolerance admin form to render",
        )
        self.select_by_index("id_tolerance", 1)
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

        self.driver.find_element(By.LINK_TEXT, 'simple').click()
        self.select_by_index("id_tolerance", 1)
        self.driver.find_element(By.ID, 'id_reference_value').send_keys('0')
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

        self.driver.find_element(By.LINK_TEXT, 'composite').click()
        self.select_by_index("id_tolerance", 1)
        self.driver.find_element(By.ID, 'id_reference_value').send_keys('23.23')
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

    def test_admin_statuses(self):

        self.load_admin()
        self.wait.until(
            e_c.presence_of_element_located((By.XPATH, "//a[contains(@href,'testinstancestatus')]")),
            "the test instance status changelist link on the admin index",
        )
        self.driver.find_element(By.XPATH, "//a[contains(@href,'testinstancestatus')]").click()
        self.click_by_link_text('ADD TEST INSTANCE STATUS')
        self.wait.until(
            e_c.presence_of_element_located((By.ID, 'id_name')),
            "the test instance status admin form to render",
        )
        self.driver.find_element(By.ID, 'id_name').send_keys('testStatus')
        self.driver.find_element(By.ID, 'id_is_default').click()
        self.driver.find_element(By.NAME, '_addanother').click()
        self.wait_for_success()

        self.wait.until(
            e_c.presence_of_element_located((By.ID, 'id_name')),
            "the test instance status admin form to render",
        )
        self.driver.find_element(By.ID, 'id_name').send_keys('testApprovalStatus')
        self.driver.find_element(By.ID, 'id_requires_review').click()
        self.driver.find_element(By.NAME, '_save').click()
        self.wait_for_success()

    def rest(self):

        self.load_main()

        # Perform test
        self.click_by_link_text('TestUnit')
        self.click_by_link_text('Perform')

        self.wait.until(
            e_c.presence_of_element_located((By.ID, 'id_form-0-value')),
            "the QC form's first value input to render",
        )
        basic = self.driver.find_element(By.ID, 'id_form-0-value')
        boolean = self.driver.find_element(By.NAME, 'form-1-value')
        basic.send_keys('3')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[1]/td[5][contains(text(), "ACT(3.00)")]')
            ),
            "the QC table row to show its calculated value",
        )

        basic.send_keys(Keys.BACKSPACE, '2')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[1]/td[5][contains(text(), "TOL(2.00)")]')
            ),
            "the QC table row to show its calculated value",
        )

        basic.send_keys(Keys.BACKSPACE, '1')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[1]/td[5][contains(text(), "OK(1.00)")]')
            ),
            "the QC table row to show its calculated value",
        )

        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[13]/td[5][contains(text(), "OK(0.0%)")]')
            ),
            "the QC table row to show its calculated value",
        )

        basic.send_keys(Keys.BACKSPACE, '1.06')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[13]/td[5][contains(text(), "ACT(6.0%)")]')
            ),
            "the QC table row to show its calculated value",
        )

        basic.send_keys(Keys.BACKSPACE, '5')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[13]/td[5][contains(text(), "TOL(5.0%)")]')
            ),
            "the QC table row to show its calculated value",
        )

        basic.send_keys(Keys.BACKSPACE, Keys.BACKSPACE, Keys.BACKSPACE)
        boolean.click()
        # time.sleep(1)

        multi = self.driver.find_element(By.ID, 'id_form-2-string_value')
        multi.click()
        multi.send_keys(Keys.ARROW_DOWN, Keys.ENTER)
        self.assertTrue(
            self.driver.find_element(By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[7]/td[5]').text == 'ACT'
        )
        multi.click()
        multi.send_keys(Keys.ARROW_DOWN, Keys.ENTER)
        self.assertTrue(
            self.driver.find_element(By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[7]/td[5]').text == 'TOL'
        )
        multi.click()
        multi.send_keys(Keys.ARROW_DOWN, Keys.ENTER)
        self.assertTrue(
            self.driver.find_element(By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[7]/td[5]').text == 'OK'
        )

        self.driver.find_element(By.ID, 'id_form-5-string_value').send_keys('a string')
        boolean.click()
        self.wait.until(
            e_c.text_to_be_present_in_element_value((By.ID, 'id_form-6-string_value'), 'a string composite'),
            "the string composite test to be recalculated",
        )

        self.driver.find_element(By.ID, 'id_form-7-skipped').click()

        self.driver.find_element(By.ID, 'submit-qa').click()

        self.wait.until(
            e_c.presence_of_element_located((By.XPATH, '//div[contains(text(), "Showing 1 to 1")]')),
            "the unreviewed listing to show exactly one row",
        )
        self.driver.find_element(By.PARTIAL_LINK_TEXT, 'Review Data').click()
        self.driver.find_element(By.PARTIAL_LINK_TEXT, 'Unreviewed Visible To Your Groups').click()
        self.click_by_link_text('Review')

        self.wait.until(
            e_c.presence_of_element_located((By.ID, 'id_testinstance_set-0-status')),
            "the review form to render",
        )
        self.driver.find_element(By.ID, 'bulk-status').click()
        self.driver.find_element(By.ID, 'bulk-status').send_keys(Keys.ARROW_DOWN, Keys.ARROW_DOWN, Keys.ENTER)

        self.driver.find_element(By.XPATH, '//button[@type = "submit"]').click()

        self.wait.until(
            e_c.presence_of_element_located((By.XPATH, '//td[contains(text(), "No data available in table")]')),
            "the unreviewed listing to empty after the review",
        )


@pytest.mark.selenium
class TestPerformQC(BaseQATests):

    def setUp(self):
        with transaction.atomic():
            super().setUp()

            self.unit = utils.create_unit()
            self.group = utils.create_group()
            for p in Permission.objects.all():
                self.group.permissions.add(p)
            self.user.groups.add(self.group)
            self.test_list = utils.create_test_list()

            self.tnum_1 = utils.create_test(name="test1")
            self.tnum_2 = utils.create_test(name="test2")
            self.tcomp = utils.create_test(name="testc", test_type=models.COMPOSITE)
            self.tcomp.calculation_procedure = "result = test1 + test2 + 2"
            self.tcomp.save()

            self.tdate = utils.create_test(name="testdate", test_type=models.DATE)
            self.tdatetime = utils.create_test(name="testdatetime", test_type=models.DATETIME)

            self.tmult = utils.create_test(name="testmult", choices="choicea,choiceb", test_type=models.MULTIPLE_CHOICE)
            self.tstring = utils.create_test(name="teststring", test_type=models.STRING)
            self.tstringcomp = utils.create_test(name="teststringcomp", test_type=models.STRING_COMPOSITE)
            self.tstringcomp.calculation_procedure = "teststringcomp = teststring + testmult"
            self.tstringcomp.save()

            all_tests = [
                self.tnum_1,
                self.tnum_2,
                self.tcomp,
                self.tdate,
                self.tdatetime,
                self.tmult,
                self.tstring,
                self.tstringcomp,
            ]

            for o, t in enumerate(all_tests):
                utils.create_test_list_membership(self.test_list, t, order=o)

            self.utc = utils.create_unit_test_collection(unit=self.unit, test_collection=self.test_list)

            self.utc.visible_to.add(self.group)
            self.url = reverse("perform_qa", kwargs={'pk': self.utc.pk})
            self.status = models.TestInstanceStatus.objects.create(
                name="foo",
                slug="foo",
                is_default=True,
            )

            sl_utils.create_service_event_status(is_default=True)
            sl_utils.create_unit_service_area(self.utc.unit)
            sl_utils.create_service_type()

    def test_ok_on_load(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""
        with transaction.atomic():
            self.login()
            self.open(self.url)
            assert len(self.driver.find_elements(By.CSS_SELECTOR, ".qa-status.btn-danger")) == 0

    def fill_testlist(self):

        self.login()
        self.open(self.url)
        inputs = self.wait_for_elements(By.CLASS_NAME, "qa-input", minimum=2)[:3]
        inputs[0].send_keys(1)
        inputs[1].send_keys(2)
        inputs[1].send_keys(Keys.TAB)
        self.wait_for_ajax()
        self.click_by_css_selector(".choose-date")
        self.wait.until(
            e_c.element_to_be_clickable((By.CSS_SELECTOR, ".open .today")),
            "the open date picker's 'today' cell to become clickable",
        )
        self.click_by_css_selector(".open .today")

        self.click_by_css_selector(".choose-datetime")
        self.wait.until(
            e_c.element_to_be_clickable((By.CSS_SELECTOR, ".open .today")),
            "the open date picker's 'today' cell to become clickable",
        )
        self.click_by_css_selector(".open .today")

        self.click_by_css_selector("body")

        option = self.wait_for_elements(By.CSS_SELECTOR, "select.qa-input option")[-1]
        option.click()

        self.driver.find_element(By.CSS_SELECTOR, ".qa-string .qa-input").send_keys("test")
        self.click_by_css_selector("body")
        self.wait_for_ajax()

    def test_perform_ok(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""

        self.fill_testlist()
        inputs = self.wait_for_elements(By.CLASS_NAME, "qa-input", minimum=2)[:3]

        assert int(float(inputs[2].get_attribute("value"))) == 5
        assert models.TestListInstance.objects.count() == 0
        self.click("submit-qa")
        self.wait.until(
            e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
            "the success alert after the save",
        )
        self.wait_for_ajax()

        assert models.TestListInstance.objects.count() == 1
        assert models.TestListInstance.objects.latest("pk").include_for_scheduling

        assert models.TestInstance.objects.filter(unit_test_info__test__type="simple")[0].value == 1
        assert models.TestInstance.objects.filter(unit_test_info__test__type="simple")[1].value == 2
        assert models.TestInstance.objects.get(unit_test_info__test__type="composite").value == 5
        now = timezone.now()
        date = timezone.localtime(now).date()
        assert models.TestInstance.objects.get(unit_test_info__test__type="date").date_value == date
        dt = timezone.localtime(now).replace(hour=12, minute=0, second=0, microsecond=0)
        assert models.TestInstance.objects.get(unit_test_info__test__type="datetime").datetime_value == dt
        assert models.TestInstance.objects.get(unit_test_info__test__type="string").string_value == "test"
        assert models.TestInstance.objects.get(unit_test_info__test__type="scomposite").string_value == "testchoiceb"
        assert models.TestInstance.objects.get(unit_test_info__test__type="multchoice").string_value == "choiceb"

    def test_perform_ok_therapist(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""

        self.group.permissions.clear()
        self.user.is_superuser = False
        self.user.save()
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(models.TestListInstance)
        perm, _ = Permission.objects.get_or_create(
            codename="add_testlistinstance", content_type=ct, defaults={"name": "Can add test list instance"}
        )
        self.group.permissions.add(perm)
        self.fill_testlist()
        inputs = self.wait_for_elements(By.CLASS_NAME, "qa-input", minimum=2)[:3]

        assert int(float(inputs[2].get_attribute("value"))) == 5
        assert models.TestListInstance.objects.count() == 0
        self.click("submit-qa")
        self.wait.until(
            e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
            "the success alert after the save",
        )
        self.wait_for_ajax()

        assert models.TestListInstance.objects.count() == 1
        assert models.TestListInstance.objects.latest("pk").include_for_scheduling

        assert models.TestInstance.objects.filter(unit_test_info__test__type="simple")[0].value == 1
        assert models.TestInstance.objects.filter(unit_test_info__test__type="simple")[1].value == 2
        assert models.TestInstance.objects.get(unit_test_info__test__type="composite").value == 5
        now = timezone.now()
        date = timezone.localtime(now).date()
        assert models.TestInstance.objects.get(unit_test_info__test__type="date").date_value == date
        dt = timezone.localtime(now).replace(hour=12, minute=0, second=0, microsecond=0)
        assert models.TestInstance.objects.get(unit_test_info__test__type="datetime").datetime_value == dt
        assert models.TestInstance.objects.get(unit_test_info__test__type="string").string_value == "test"
        assert models.TestInstance.objects.get(unit_test_info__test__type="scomposite").string_value == "testchoiceb"
        assert models.TestInstance.objects.get(unit_test_info__test__type="multchoice").string_value == "choiceb"

    def test_comment(self):
        """ tests present"""
        self.fill_testlist()
        self.wait_for_elements(By.CSS_SELECTOR, ".revealcomment")[0].click()
        self.send_keys("id_form-0-comment", "testticomment")
        self.wait_for_elements(By.CSS_SELECTOR, ".revealcomment")[0].click()

        self.click("submit-qa")
        self.wait.until(
            e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
            "the success alert after the save",
        )
        assert models.TestInstance.objects.filter(comment="testticomment").count() == 1

    def test_set_in_progress(self):
        """ tests present"""
        self.fill_testlist()

        self.click("in-progress-container")
        self.click("submit-qa")
        self.wait.until(
            e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
            "the success alert after the save",
        )
        assert models.TestListInstance.objects.in_progress().count() == 1

    def test_perform_and_review(self):
        """Ensure that we can go through a full perform->review cycle"""

        utils.create_status(name="reviewed", slug="reviewed", is_default=False, requires_review=False)
        self.fill_testlist()
        self.click("submit-qa")
        self.wait.until(
            e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
            "the success alert after the save",
        )

        self.open("/qc/session/unreviewed/")
        self.wait_for_ajax()

        self.click_by_link_text("Review")
        self.select_by_text("bot-status-select", "reviewed")

        self.send_keys("id_comment", "testlistcomment")
        self.click("post-comment")
        self.wait_until(lambda: models.Comment.objects.count() == 1, "the comment to be saved")
        assert models.Comment.objects.count() == 1

        assert models.TestListInstance.objects.unreviewed().count() == 1
        self.click("submit-review")
        self.wait.until(
            e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
            "the success alert after the save",
        )
        assert models.TestListInstance.objects.unreviewed().count() == 0

    def test_perform_qc_viewport_sizes(self):
        """Ensure the perform-QC page's controls stay reachable at a range of common desktop viewport sizes"""

        # A varied matrix, not just the suite's 1920x1080. 1366x768 is a very
        # common laptop resolution, and 960x1080 is the perform-QC page in half
        # of a tiled 1920x1080 display - the kind of real width a viewport
        # override capped to the real window (see set_viewport_size) has to
        # render rather than overflow.
        profiles = [
            ('half_screen_side_by_side', 960, 1080),
            ('small_laptop', 1366, 768),
            ('full_hd', 1920, 1080),
        ]

        for label, width, height in profiles:
            with self.subTest(profile=label, width=width, height=height):
                if not self.set_viewport_size(width, height):
                    # The viewport could not actually be changed - a visible
                    # Firefox under a Wayland compositor, typically. Skipping
                    # is the honest outcome: without the override every
                    # profile renders at whatever size the window manager
                    # gave, so the test would pass three times over at one
                    # size and claim to have checked three.
                    self.skipTest(
                        "viewport override unavailable; cannot test %s at %dx%d"
                        % (label, width, height)
                    )
                self.fill_testlist()

                inputs = self.wait_for_elements(By.CLASS_NAME, "qa-input", minimum=2)[:3]
                assert int(float(inputs[2].get_attribute("value"))) == 5

                submit = self.driver.find_element(By.ID, "submit-qa")
                assert submit.is_displayed()
                rect = self.driver.execute_script(
                    "var r = arguments[0].getBoundingClientRect();"
                    "return {left: r.left, right: r.right, vw: window.innerWidth};",
                    submit,
                )
                assert 0 <= rect['left'] and rect['right'] <= rect['vw'], (
                    "submit-qa rendered outside the %sx%s viewport (profile=%s): %s"
                    % (width, height, label, rect)
                )
                # Clickable, not merely within bounds per
                # getBoundingClientRect: a logical viewport wider than the
                # real window leaves content "inside" it and unclickable.
                submit.click()
                self.wait.until(
                    e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
                    "the success alert after the save",
                )

    def test_perform_and_initiate_se(self):
        """Ensure that we can go through a full perform->review cycle"""

        self.fill_testlist()
        self.click("init-se-container")
        self.click("submit-qa")

        self.wait.until(
            e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
            "the success alert after the save",
        )

        # flatpickr binds the calendar from sl_serviceevent.js after the
        # page's JS runs; focusing before that just focuses a text box. It
        # records its instance on the element, so wait for that.
        self.wait.until(
            lambda d: d.execute_script(
                "var el = document.getElementById('id_datetime_service');"
                "return !!(el && el._flatpickr);"
            ),
            "the service event datetime field to be populated",
        )
        self.execute_jquery_script("$('#id_datetime_service').focus()")

        # The calendar, not wait_for_ajax(). jQuery.active is a whole-page
        # condition, so an unrelated request on this form keeps it above zero
        # and the wait can burn the full timeout with the calendar already
        # open. The click below needs the calendar; wait for that.
        self.wait.until(
            e_c.visibility_of_element_located((By.CSS_SELECTOR, ".flatpickr-calendar.open")),
            "the service event date picker to open",
        )
        self.click_by_css_selector(".today")
        # The value, not wait_for_ajax(), for the same reason as the calendar
        # wait above: this form keeps its own requests in flight, so the
        # whole-page condition can outlast `.today` writing the value.
        self.wait.until(
            lambda d: d.execute_script(
                "var el = document.getElementById('id_datetime_service');"
                "return !!(el && el.value);"
            ),
            "the service event datetime field to be populated",
        )
        self.select_by_index("id_service_area_field_fake", 1)
        # The visible select is a decoy: its change handler copies the value
        # into the hidden service_area_field, which is required and is what
        # actually submits. That copy is synchronous DOM work with no request
        # behind it, so an AJAX wait here waits for nothing. Assert the copy
        # instead, so losing it fails here naming the field rather than at the
        # save as a validation error.
        self.wait.until(
            lambda d: d.execute_script(
                "var el = document.getElementById('id_service_area_field');"
                "return !!(el && el.value);"
            ),
            "the service area to be copied into the submitted field",
        )
        self.select_by_index("id_service_type", 1)
        self.send_keys("id_problem_description", "Problem!")
        self.click("save-se")
        # The save is what matters, not the page going quiet - wait on the
        # server-side result so a slow save reports as a timeout naming the
        # condition rather than as a bare `0 == 1` assertion failure.
        self.wait_until(
            lambda: models.TestListInstance.objects.first().serviceevents_initiated.count() == 1,
            "the service event to be linked to the test list instance",
        )
        assert models.TestListInstance.objects.first().serviceevents_initiated.count() == 1

    def test_autosave(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""

        self.login()
        self.open(self.url)
        # No sleep needed before wait_for_elements - waiting is what it does.
        inputs = self.wait_for_elements(By.CLASS_NAME, "qa-input", minimum=2)[:3]
        inputs[0].send_keys(1)
        assert models.AutoSave.objects.count() == 0
        # Paces the simulated typing so the debounce timer starts from the
        # first keystroke before Enter. Not an observable condition, so there
        # is nothing to wait on instead; without it autosave never fires.
        time.sleep(1)
        inputs[0].send_keys(Keys.ENTER)
        # Autosave is debounced on a 4s interval. This used to sleep a flat
        # 4.2s and then assert; polling instead returns as soon as the row
        # lands, and still tolerates a slow run rather than failing at 4.2s.
        self.wait_until(
            lambda: models.AutoSave.objects.count() == 1,
            "the debounced autosave to be written",
            timeout=max(self.timeout, 10),
        )
        assert models.AutoSave.objects.count() == 1

    def test_load_autosave(self):
        """Ensure an autosave is restored with its test values, comments and
        work started/completed times displayed in the sites datetime format"""

        tl2 = utils.create_test_list(name="day 2")
        utils.create_test_list_membership(tl2, test=self.tnum_1)
        cycle = utils.create_cycle([self.test_list, tl2])
        utc = utils.create_unit_test_collection(
            unit=self.utc.unit, test_collection=cycle, assigned_to=self.utc.assigned_to
        )

        tz = timezone.get_current_timezone()
        auto = models.AutoSave.objects.create(
            unit_test_collection=utc,
            test_list=tl2,
            day=1,
            work_started=timezone.datetime(1980, 5, 12, 12).replace(tzinfo=tz),
            work_completed=timezone.datetime(1980, 5, 12, 12, 1).replace(tzinfo=tz),
            created_by=self.user,
            modified_by=self.user,
            data={
                'tests': {
                    'test1': 1,
                },
                'comments': {
                    'test1': 'test comment',
                },
                'skips': {
                    'test1': False,
                },
                'tli_comment': 'test list instance comment'
            }
        )

        self.login()

        url = reverse("perform_qa", kwargs={'pk': utc.pk})
        self.open(url + "?autosave_id=%d&day=%d" % (auto.pk, auto.day + 1))
        self.wait_for_ajax()

        inputs = self.wait_for_elements(By.CLASS_NAME, "qa-input", minimum=2)[:3]
        title = "Perform %s : day 2" % utc.unit.name
        # wait_for_elements, not find_elements: with the implicit wait off,
        # find_elements returns whatever has rendered so far, which on a
        # still-settling page can be an empty list.
        assert title in [el.text for el in self.wait_for_elements(By.CLASS_NAME, "box-title")]

        # The values arrive after the inputs do, so wait for one to be filled
        # rather than to exist. Reading too early yields "", which surfaces as
        # "could not convert string to float: ''".
        self.wait.until(
            lambda d: inputs[0].get_attribute("value") != "",
            "the first test input to be populated",
        )
        assert float(inputs[0].get_attribute("value")) == 1
        # flatpickr's setDate() redisplays using the configured datetime
        # format, not the human format a freshly-rendered field uses. Derived
        # rather than literal, so it survives a format change (see #832).
        started = date_format(timezone.datetime(1980, 5, 12, 12, 0), get_format('DATETIME_FORMAT'))
        completed = date_format(timezone.datetime(1980, 5, 12, 12, 1), get_format('DATETIME_FORMAT'))
        assert self.driver.find_element(By.ID, "id_work_started").get_attribute("value") == started
        assert self.driver.find_element(By.ID, "id_work_completed").get_attribute("value") == completed
        assert self.driver.find_element(By.ID, "id_work_duration").get_attribute("value") == "0hr:01min"
        assert self.driver.find_element(By.ID, "id_form-0-comment").get_attribute("value") == "test comment"
        assert self.driver.find_element(By.ID, "id_comment").get_attribute("value") == "test list instance comment"

    def test_submit_autosave(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""

        tl2 = utils.create_test_list(name="day 2")
        utils.create_test_list_membership(tl2, test=self.tnum_1)
        cycle = utils.create_cycle([self.test_list, tl2])
        utc = utils.create_unit_test_collection(
            unit=self.utc.unit, test_collection=cycle, assigned_to=self.utc.assigned_to
        )

        tz = timezone.get_current_timezone()
        auto = models.AutoSave.objects.create(
            unit_test_collection=utc,
            test_list=tl2,
            day=1,
            work_started=timezone.datetime(1980, 5, 12, 12).replace(tzinfo=tz),
            work_completed=timezone.datetime(1980, 5, 12, 12, 1).replace(tzinfo=tz),
            created_by=self.user,
            modified_by=self.user,
            data={
                'tests': {
                    'test1': 1,
                },
                'comments': {
                    'test1': 'test comment',
                },
                'skips': {
                    'test1': False,
                },
                'tli_comment': 'test list instance comment'
            }
        )

        self.login()

        url = reverse("perform_qa", kwargs={'pk': utc.pk})
        self.open(url + "?autosave_id=%d&day=%d" % (auto.pk, auto.day + 1))
        self.wait_for_ajax()

        self.click("submit-qa")
        # click() returns when the click is dispatched, not when the POST it
        # triggers is handled, so the assertion below would race the
        # submission. Every other submit-qa test here waits for this alert.
        self.wait.until(
            e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
            "the success alert after the save",
        )

        assert models.AutoSave.objects.filter(pk=auto.pk).count() == 0





def bulk_review_initialised(driver):
    """Truthy once qabulkreview.js has run *and* the filter row has settled.

    The page renders several `.test-selected-toggle` checkboxes from a single
    declaration, because DataTables clones the header row - measured on
    /qc/session/unreviewed/: three, in thead rows 0 and 1 and tfoot row 0. The
    exact number is a DataTables detail and not worth depending on, so the
    predicate only asserts what it needs:

    - at least two exist, so the clones are in place
    - at least one is hidden, which is qabulkreview.js having run, and
      therefore its change handler being bound
    - index 0 is visible, so it is the one a caller can actually click

    Both of the last two are required. jQuery.active is 0 throughout the
    window between them, so an AJAX wait returns inside it. Waiting only for
    "a visible toggle" is satisfied before the hide, when the handler is not
    yet bound and a click does nothing.

    Returns the toggles so a caller can `.until(...)[0].click()`.
    """
    toggles = driver.find_elements(By.CLASS_NAME, "test-selected-toggle")
    if len(toggles) < 2:
        return False
    shown = [t.is_displayed() for t in toggles]
    return toggles if (not all(shown) and shown[0]) else False


class TestReviewQC(BaseQATests):

    def setUp(self):
        with transaction.atomic():
            super().setUp()

            self.unreviewed = utils.create_status(name="Unreviewed", slug="unreviewed")
            self.reviewed = utils.create_status(name="Approved", slug="approved", is_default=False, requires_review=False)
            utils.create_test_instance()

            self.url = "/qc/session/unreviewed/"

    @override_settings(REVIEW_BULK=True)
    def test_bulk_review_gate_rejects_every_premature_state(self):
        """Drive the DOM to each state the gate must reject, deterministically.

        The race this gate exists for is roughly one page load in five on the
        machine that reported it, and does not reproduce here at all - eight
        consecutive runs never saw the gate block once. So waiting for the
        window to occur is not a test; constructing it is.

        Each case sets the first two toggles' visibility directly and asks the
        predicate, which is the whole of its input. Any further clones are left
        visible, which is what the settled page looks like anyway.
        """
        with transaction.atomic():
            self.login()
            self.open(self.url)
            self.wait.until(bulk_review_initialised, "the bulk review JS to initialise")

            # Only the first two matter: the predicate keys off "not all
            # visible" and "index 0 visible", so clones beyond index 1 stay as
            # they are.
            def set_visibility(first, second):
                self.driver.execute_script(
                    "var els = document.getElementsByClassName('test-selected-toggle');"
                    "els[0].style.display = arguments[0] ? '' : 'none';"
                    "els[1].style.display = arguments[1] ? '' : 'none';",
                    first,
                    second,
                )

            # Before qabulkreview.js runs: both visible, no change handler
            # bound yet. This is the state "click the first visible toggle"
            # would accept, and the click would do nothing.
            set_visibility(True, True)
            assert not bulk_review_initialised(self.driver), "accepted the pre-hide state"

            # After the hide, before the reorder: index 0 is the hidden one,
            # so clicking index 0 is clicking something invisible.
            set_visibility(False, True)
            assert not bulk_review_initialised(self.driver), "accepted the mid-window state"

            # Settled: the hidden toggle has moved to index 1.
            set_visibility(True, False)
            toggles = bulk_review_initialised(self.driver)
            assert toggles, "rejected the settled state"
            assert toggles[0].is_displayed()

    @override_settings(REVIEW_BULK=True)
    def test_review_ok(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""
        with transaction.atomic():
            self.login()
            self.open(self.url)
            self.wait_for_ajax()
            self.wait.until(
                bulk_review_initialised,
                "the bulk review JS to hide the filter row's select-all checkbox",
            )[0].click()
            self.select_by_text("bulk-status", "Approved")
            self.click("submit-review")
            assert models.TestListInstance.objects.unreviewed().count() == 1

            self.click("confirm-update")
            self.wait.until(
                e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')),
                "the success alert after the save",
            )
            assert models.TestListInstance.objects.unreviewed().count() == 0



