import time

from django.conf import settings
from django.contrib.auth.models import Permission
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as e_c

from qatrack.accounts.tests.utils import create_group, create_user
from qatrack.qa import models
from qatrack.qa.tests import utils
from qatrack.qatrack_core.tests.live import SeleniumTests
from qatrack.qatrack_core.utils import format_as_date
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


class BaseQATests(SeleniumTests):

    def setUp(self):

        self.password = 'password'
        self.user = create_user(pwd=self.password)

    def login(self):
        self.open("/accounts/login/")
        self.send_keys("id_username", self.user.username)
        self.send_keys("id_password", self.password)
        self.driver.find_element_by_css_selector('button').click()

        self.wait.until(e_c.presence_of_element_located((By.CSS_SELECTOR, "head > title")))

    def load_main(self):
        self.login()
        self.open("")

    def load_admin(self):
        self.open("/admin/")
        self.send_keys("id_username", self.user.username)
        self.send_keys("id_password", self.password)
        self.driver.find_element_by_css_selector('button').click()

        self.wait.until(e_c.presence_of_element_located((By.CSS_SELECTOR, "head > title")))


@pytest.mark.selenium
class LiveQATests(BaseQATests):

    def setUp(self):

        super().setUp()

    def test_admin_category(self):

        self.load_admin()
        self.driver.find_element_by_xpath('//a[@href="/admin/qa/category/"]').click()
        self.click_by_link_text("ADD CATEGORY")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys(objects['Category']['name'])
        self.driver.find_element_by_id('id_slug').send_keys(objects['Category']['slug'])
        self.driver.find_element_by_id('id_description').send_keys(objects['Category']['description'])
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_tests(self):

        self.load_admin()

        if not utils.exists('qa', 'Category', 'name', objects['Category']['name']):
            utils.create_category(
                name=objects['Category']['name'],
                slug=objects['Category']['slug'],
                description=objects['Category']['description'],
            )

        self.driver.find_element_by_link_text('Tests').click()
        self.click_by_link_text("ADD TEST")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        # for i in range(len(objects['Tests'])):

        for i in range(len(objects['Tests'])):
            # the_test = objects['Tests'][i]
            the_test = objects['Tests'][i]
            self.send_keys('id_name', the_test['name'])
            self.send_keys('id_slug', the_test['name'])
            self.select_by_index('id_category', 1)
            self.select_by_value('id_type', the_test['name'])
            time.sleep(0.1)

            if the_test['choices']:
                self.send_keys('id_choices', '1,2,3,4,5')
            if the_test['constant_value']:
                self.send_keys('id_constant_value', '23.23')
            if the_test['procedure']:
                time.sleep(1)
                self.driver.find_element_by_css_selector('#calc-procedure-editor > textarea').send_keys(
                    the_test['procedure'],
                )
                self.driver.find_element_by_css_selector('.submit-row').click()

            # Firefox webdriver being weird with clicks. Had to use javascript here:
            if i + 1 == len(objects['Tests']):
                self.driver.execute_script("$('input[name=_save]').click();")
            else:
                self.driver.execute_script("$('input[name=_addanother]').click();")

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

        self.click_by_link_text("Test lists")
        self.click_by_link_text("ADD TEST LIST")
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
        self.click_by_link_text("Modalities")
        self.click_by_link_text("ADD MODALITY")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys(objects['Modality']['name'])
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_unittype(self):

        self.load_admin()
        self.click_by_link_text("Unit types")
        self.click_by_link_text("ADD UNIT TYPE")
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
        self.click_by_link_text("Units")
        self.click_by_link_text("ADD UNIT")
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_name')))
        self.driver.find_element_by_id('id_name').send_keys(objects['Unit']['name'])
        self.driver.find_element_by_id('id_number').send_keys(objects['Unit']['number'])
        self.driver.find_element_by_id('id_date_acceptance').send_keys(objects['Unit']['date_acceptance'])
        if settings.USE_SERVICE_LOG:
            self.driver.find_element_by_css_selector('#id_service_areas_add_all_link').click()
        self.select_by_index("id_type", 1)
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
        self.click_by_link_text("Frequencies")
        self.click_by_link_text("ADD FREQUENCY")
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
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_unit')))

        self.select_by_index("id_unit", 1)
        self.select_by_index("id_frequency", 1)
        self.select_by_index("id_assigned_to", 0)
        self.select_by_index("id_content_type", 1)
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
        self.click_by_link_text('Tolerances')
        self.click_by_link_text('ADD TOLERANCE')
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_type')))
        self.select_by_index("id_type", 1)
        self.driver.find_element_by_id('id_act_low').send_keys(objects['absoluteTolerance']['act_low'])
        self.driver.find_element_by_id('id_tol_low').send_keys(objects['absoluteTolerance']['tol_low'])
        self.driver.find_element_by_id('id_tol_high').send_keys(objects['absoluteTolerance']['tol_high'])
        self.driver.find_element_by_id('id_act_high').send_keys(objects['absoluteTolerance']['act_high'])
        self.driver.find_element_by_name('_addanother').click()
        self.wait_for_success()

        # Add percentage tolerance
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_type')))
        self.select_by_index("id_type", 1)
        self.driver.find_element_by_id('id_act_low').send_keys(objects['percentTolerance']['act_low'])
        self.driver.find_element_by_id('id_tol_low').send_keys(objects['percentTolerance']['tol_low'])
        self.driver.find_element_by_id('id_tol_high').send_keys(objects['percentTolerance']['tol_high'])
        self.driver.find_element_by_id('id_act_high').send_keys(objects['percentTolerance']['act_high'])
        self.driver.find_element_by_name('_addanother').click()
        self.wait_for_success()

        # Add multi tolerance
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_type')))
        self.select_by_index("id_type", 3)
        self.driver.find_element_by_id('id_mc_pass_choices').send_keys(
            objects['multiChoiceTolerance']['mc_pass_choices']
        )
        self.driver.find_element_by_id('id_mc_tol_choices').send_keys(objects['multiChoiceTolerance']['mc_tol_choices'])
        self.driver.find_element_by_name('_save').click()
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
        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_tolerance')))
        self.select_by_index("id_tolerance", 1)
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

        self.driver.find_element_by_link_text('simple').click()
        self.select_by_index("id_tolerance", 1)
        self.driver.find_element_by_id('id_reference_value').send_keys('0')
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

        self.driver.find_element_by_link_text('composite').click()
        self.select_by_index("id_tolerance", 1)
        self.driver.find_element_by_id('id_reference_value').send_keys('23.23')
        self.driver.find_element_by_name('_save').click()
        self.wait_for_success()

    def test_admin_statuses(self):

        self.load_admin()
        self.wait.until(e_c.presence_of_element_located((By.XPATH, "//a[contains(@href,'testinstancestatus')]")))
        self.driver.find_element_by_xpath("//a[contains(@href,'testinstancestatus')]").click()
        self.click_by_link_text('ADD TEST INSTANCE STATUS')
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
        self.click_by_link_text('TestUnit')
        self.click_by_link_text('Perform')

        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_form-0-value')))
        basic = self.driver.find_element_by_id('id_form-0-value')
        boolean = self.driver.find_element_by_name('form-1-value')
        basic.send_keys('3')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[1]/td[5][contains(text(), "ACT(3.00)")]')
            )
        )

        basic.send_keys(Keys.BACKSPACE, '2')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[1]/td[5][contains(text(), "TOL(2.00)")]')
            )
        )

        basic.send_keys(Keys.BACKSPACE, '1')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[1]/td[5][contains(text(), "OK(1.00)")]')
            )
        )

        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[13]/td[5][contains(text(), "OK(0.0%)")]')
            )
        )

        basic.send_keys(Keys.BACKSPACE, '1.06')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[13]/td[5][contains(text(), "ACT(6.0%)")]')
            )
        )

        basic.send_keys(Keys.BACKSPACE, '5')
        boolean.click()
        self.wait.until(
            e_c.presence_of_element_located(
                (By.XPATH, '//*[@id="perform-qa-table"]/tbody/tr[13]/td[5][contains(text(), "TOL(5.0%)")]')
            )
        )

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
        self.click_by_link_text('Review')

        self.wait.until(e_c.presence_of_element_located((By.ID, 'id_testinstance_set-0-status')))
        self.driver.find_element_by_id('bulk-status').click()
        self.driver.find_element_by_id('bulk-status').send_keys(Keys.ARROW_DOWN, Keys.ARROW_DOWN, Keys.ENTER)

        self.driver.find_element_by_xpath('//button[@type = "submit"]').click()

        self.wait.until(
            e_c.presence_of_element_located((By.XPATH, '//td[contains(text(), "No data available in table")]'))
        )


@pytest.mark.selenium
class TestPerformQC(BaseQATests):

    def setUp(self):

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

    def test_ok_on_load(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""
        self.login()
        self.open(self.url)
        assert len(self.driver.find_elements_by_css_selector(".qa-status.btn-danger")) == 0

    def fill_testlist(self):

        self.login()
        self.open(self.url)
        inputs = self.driver.find_elements_by_class_name("qa-input")[:3]
        inputs[0].send_keys(1)
        inputs[1].send_keys(2)
        inputs[1].send_keys(Keys.TAB)
        time.sleep(0.2)

        self.click_by_css_selector(".choose-date")
        time.sleep(0.2)
        self.click_by_css_selector(".open .today")

        self.click_by_css_selector(".choose-datetime")
        time.sleep(0.2)
        self.click_by_css_selector(".open .today")

        self.click_by_css_selector("body")

        option = self.driver.find_elements_by_css_selector("select.qa-input option")[-1]
        option.click()

        self.driver.find_element_by_css_selector(".qa-string .qa-input").send_keys("test")
        self.click_by_css_selector("body")
        time.sleep(0.2)

    def fill_se(self):

        time.sleep(0.2)
        self.driver.execute_script("$('#id_datetime_service').focus()")
        time.sleep(0.3)
        self.click_by_css_selector(".today")
        time.sleep(0.2)
        self.send_keys("id_problem_description", "Problem!")

    def test_perform_ok(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""

        self.fill_testlist()
        inputs = self.driver.find_elements_by_class_name("qa-input")[:3]

        assert int(float(inputs[2].get_attribute("value"))) == 5
        assert models.TestListInstance.objects.count() == 0
        self.click("submit-qa")
        self.wait.until(e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')))

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
        self.group.permissions.add(Permission.objects.get(codename="add_testlistinstance"))
        self.fill_testlist()
        inputs = self.driver.find_elements_by_class_name("qa-input")[:3]

        assert int(float(inputs[2].get_attribute("value"))) == 5
        assert models.TestListInstance.objects.count() == 0
        self.click("submit-qa")
        self.wait.until(e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')))

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
        self.driver.find_elements_by_css_selector(".revealcomment")[0].click()
        self.send_keys("id_form-0-comment", "testticomment")
        self.driver.find_elements_by_css_selector(".revealcomment")[0].click()

        self.click("submit-qa")
        self.wait.until(e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')))
        assert models.TestInstance.objects.filter(comment="testticomment").count() == 1

    def test_set_in_progress(self):
        """ tests present"""
        self.fill_testlist()

        self.click("in-progress-container")
        self.click("submit-qa")
        self.wait.until(e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')))
        assert models.TestListInstance.objects.in_progress().count() == 1

    def test_perform_and_review(self):
        """Ensure that we can go through a full perform->review cycle"""

        utils.create_status(name="reviewed", slug="reviewed", is_default=False, requires_review=False)
        self.fill_testlist()
        self.click("submit-qa")
        self.wait.until(e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')))

        self.open("/qc/session/unreviewed/")
        time.sleep(0.2)

        self.click_by_link_text("Review")
        self.select_by_text("bot-status-select", "reviewed")

        self.send_keys("id_comment", "testlistcomment")
        self.click("post-comment")
        time.sleep(0.2)
        assert models.Comment.objects.count() == 1

        assert models.TestListInstance.objects.unreviewed().count() == 1
        self.click("submit-review")
        self.wait.until(e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')))
        assert models.TestListInstance.objects.unreviewed().count() == 0

    @override_settings(SL_ALLOW_BLANK_SERVICE_AREA=True, SL_ALLOW_BLANK_SERVICE_TYPE=True)
    def test_perform_and_initiate_se(self):
        """Ensure that we can go through a full perform->review cycle"""

        self.fill_testlist()
        self.click("init-se-container")
        self.click("submit-qa")

        self.wait.until(e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')))

        self.fill_se()
        self.click("save-se")
        time.sleep(0.2)
        assert models.TestListInstance.objects.first().serviceevents_initiated.count() == 1

    def test_autosave(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""

        self.login()
        self.open(self.url)
        time.sleep(0.2)
        inputs = self.driver.find_elements_by_class_name("qa-input")[:3]
        inputs[0].send_keys(1)
        assert models.AutoSave.objects.count() == 0
        time.sleep(1)
        inputs[0].send_keys(Keys.ENTER)
        time.sleep(2.1)  # auto save is debounced with a 2s interval
        assert models.AutoSave.objects.count() == 1

    def test_load_autosave(self):
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
            work_started=tz.localize(timezone.datetime(1980, 5, 12, 12)),
            work_completed=tz.localize(timezone.datetime(1980, 5, 12, 12, 1)),
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
        time.sleep(0.2)

        inputs = self.driver.find_elements_by_class_name("qa-input")[:3]
        title = "Perform %s : day 2" % utc.unit.name
        assert title in [el.text for el in self.driver.find_elements_by_class_name("box-title")]
        assert float(inputs[0].get_attribute("value")) == 1
        assert self.driver.find_element_by_id("id_work_started").get_attribute("value") == "12 May 1980 12:00"
        assert self.driver.find_element_by_id("id_work_completed").get_attribute("value") == "12 May 1980 12:01"
        assert self.driver.find_element_by_id("id_work_duration").get_attribute("value") == "0hr:01min"
        assert self.driver.find_element_by_id("id_form-0-comment").get_attribute("value") == "test comment"
        assert self.driver.find_element_by_id("id_comment").get_attribute("value") == "test list instance comment"

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
            work_started=tz.localize(timezone.datetime(1980, 5, 12, 12)),
            work_completed=tz.localize(timezone.datetime(1980, 5, 12, 12, 1)),
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
        time.sleep(0.2)

        self.click("submit-qa")

        assert models.AutoSave.objects.filter(pk=auto.pk).count() == 0


@pytest.mark.selenium
class TestReviewQC(BaseQATests):

    def setUp(self):

        super().setUp()

        self.unreviewed = utils.create_status(name="Unreviewed", slug="unreviewed")
        self.reviewed = utils.create_status(name="Approved", slug="approved", is_default=False, requires_review=False)
        utils.create_test_instance()

        self.url = "/qc/session/unreviewed/"

    @override_settings(REVIEW_BULK=True)
    def test_review_ok(self):
        """Ensure that no failed tests on load and 3 "NO TOL" tests present"""
        self.login()
        self.open(self.url)
        time.sleep(0.1)
        self.driver.find_elements_by_class_name("test-selected-toggle")[0].click()
        self.select_by_text("bulk-status", "Approved")
        self.click("submit-review")
        assert models.TestListInstance.objects.unreviewed().count() == 1

        self.click("confirm-update")
        self.wait.until(e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')))
        assert models.TestListInstance.objects.unreviewed().count() == 0
