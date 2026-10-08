
import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from selenium.webdriver.common.by import By

from qatrack.accounts.tests.utils import create_group
from qatrack.qa.tests import utils as qa_utils
from qatrack.qa.tests.test_selenium import BaseQATests
from qatrack.service_log import models
from qatrack.service_log.tests import utils as sl_utils


@pytest.mark.selenium
class TestServiceEventForm(BaseQATests):
    """Direct create/edit coverage for the standalone Service Event form
    (/sl/event/create/, /sl/event/edit/<pk>/), which had none.

    TestPerformQC.test_perform_and_initiate_se covers only this form's
    "initiate from a QC session" shortcut embedded in the perform-QC page.
    `datetime_service` uses the same flatpickr/DateTimeInput widget family as
    the Fault form and the perform-QC page.
    """

    def setUp(self):
        super().setUp()

        # BaseQATests only creates self.user - build out enough permissions
        # and reference data for the service event form to be usable.
        self.group = create_group()
        for p in Permission.objects.all():
            self.group.permissions.add(p)
        self.user.groups.add(self.group)

        sl_utils.create_service_event_status(is_default=True)
        self.service_type = sl_utils.create_service_type()

        self.unit = qa_utils.create_unit()
        self.service_area = sl_utils.create_service_area()
        self.usa = sl_utils.create_unit_service_area(unit=self.unit, service_area=self.service_area)

    def test_create_service_event(self):
        """Create a service event directly via /sl/event/create/, not via the QC-page shortcut"""

        self.login()
        self.open(reverse('sl_new') + '?u=%d' % self.unit.pk)
        self.wait_for_ajax()

        self.select_by_index("id_service_area_field_fake", 1)
        self.wait_for_ajax()
        self.select_by_index("id_service_type", 1)
        self.execute_jquery_script("$('#id_datetime_service').focus()")
        self.wait_for_ajax()
        self.click_by_css_selector(".today")
        self.wait_for_ajax()
        self.send_keys("id_problem_description", "Something broke")
        self.send_keys("id_work_description", "Fixed it")

        se_count = models.ServiceEvent.objects.count()
        self.click("save-se")
        # A successful save redirects to the service log dashboard rather than
        # showing an alert-success banner in place, as the perform-QC flows do,
        # so wait for the navigation.
        self.wait.until(
            lambda d: d.current_url.rstrip('/').endswith('/servicelog'),
            "the browser to be redirected to /servicelog after a successful save",
        )
        self.wait_until(
            lambda: models.ServiceEvent.objects.count() == se_count + 1,
            "the service event to be saved",
        )

        assert models.ServiceEvent.objects.count() == se_count + 1
        se = models.ServiceEvent.objects.latest("pk")
        assert se.problem_description == "Something broke"
        assert se.work_description == "Fixed it"
        assert se.unit_service_area_id == self.usa.pk
        assert se.service_type_id == self.service_type.pk

    def test_edit_service_event(self):
        """Edit an existing service event via /sl/event/edit/<pk>/"""

        se = sl_utils.create_service_event(
            unit_service_area=self.usa,
            problem_description="Original problem",
        )

        self.login()
        self.open(reverse('sl_edit', kwargs={'pk': se.pk}))
        self.wait_for_ajax()

        # Check the existing value round-tripped into the field before
        # changing it: a date that loads back wrong is otherwise invisible
        # until something downstream disagrees.
        problem_field = self.driver.find_element(By.ID, "id_problem_description")
        assert problem_field.get_attribute("value") == "Original problem"

        problem_field.clear()
        problem_field.send_keys("Updated problem")

        self.click("save-se")
        # As with create, a successful save redirects to the service log
        # dashboard rather than showing an `alert-success` banner in place.
        self.wait.until(
            lambda d: d.current_url.rstrip('/').endswith('/servicelog'),
            "the browser to be redirected to /servicelog after a successful save",
        )
        self.wait_until(
            lambda: models.ServiceEvent.objects.get(pk=se.pk).problem_description == "Updated problem",
            "the edited problem description to be saved",
        )

        se.refresh_from_db()
        assert se.problem_description == "Updated problem"




