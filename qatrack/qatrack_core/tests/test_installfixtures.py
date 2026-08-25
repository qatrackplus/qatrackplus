"""
Tests for the installfixtures management command and the default fixture graph.

These tests load the default fixtures into a test database (populated by
migrations) and assert the minimum object graph required for an end-to-end
QA workflow.

All tests share a single class-level fixture load via setUpClass so that the
expensive ``installfixtures`` call runs once, and each test method merely
queries the already-populated database inside a savepoint that is rolled back
after every test.
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from qatrack.qa import models as qa_models
from qatrack.units.models import Unit


class TestDefaultFixtureGraph(TestCase):
    """Verify the minimum object graph after loading default fixtures."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        call_command('installfixtures', verbosity=0)

    def test_at_least_one_active_unit(self):
            "No active Unit found after loading default fixtures"

    def test_unit_has_scheduled_test_collection(self):
        unit = Unit.objects.filter(active=True).first()
        assert qa_models.UnitTestCollection.objects.filter(unit=unit, active=True).exists(), \
            "Active unit has no scheduled UnitTestCollection"

    def test_test_list_has_at_least_one_test(self):
        utc = qa_models.UnitTestCollection.objects.filter(active=True).first()
        assert utc is not None
        tl = utc.tests_object
        assert tl.all_tests().count() >= 1, \
            "Test list has no tests"

    def test_completed_test_list_instance_exists(self):
        assert qa_models.TestListInstance.objects.filter(
            in_progress=False,
            work_completed__isnull=False,
        ).exists(), "No completed TestListInstance found"

    def test_test_instance_exists_for_completed_tli(self):
        tli = qa_models.TestListInstance.objects.filter(
            in_progress=False,
            work_completed__isnull=False,
        ).first()
        assert qa_models.TestInstance.objects.filter(test_list_instance=tli).exists(), \
            "No TestInstance found for the completed TestListInstance"

    def test_review_page_has_instance_requiring_review(self):
        """The review workflow needs at least one instance with requires_review status."""
        assert qa_models.TestInstance.objects.filter(
            status__requires_review=True,
        ).exists(), "No TestInstance with a requires_review status found"

    def test_frequency_exists(self):
        assert qa_models.Frequency.objects.exists(), "No Frequency found"

    def test_category_exists(self):
        assert qa_models.Category.objects.exists(), "No Category found"

    def test_tolerance_exists(self):
        assert qa_models.Tolerance.objects.exists(), "No Tolerance found"

    def test_test_instance_status_exists(self):
        assert qa_models.TestInstanceStatus.objects.exists(), \
            "No TestInstanceStatus found"

    def test_default_status_is_configured(self):
        assert qa_models.TestInstanceStatus.objects.filter(is_default=True).exists(), \
            "No default TestInstanceStatus configured"

    def test_unit_test_info_exists(self):
        assert qa_models.UnitTestInfo.objects.exists(), "No UnitTestInfo found"

    def test_qatrack_internal_user_exists(self):
        assert User.objects.filter(username="QATrack+ Internal").exists(), \
            "QATrack+ Internal user is required by audit fields but was not found"

    def test_fixture_dirs_includes_service_log(self):
        service_log_dir = 'fixtures/defaults/service_log'
        assert service_log_dir in settings.FIXTURE_DIRS, \
            f"{service_log_dir!r} is not in settings.FIXTURE_DIRS"
