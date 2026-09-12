from io import StringIO
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from qatrack.faults.models import Fault
from qatrack.parts.models import Part, PartUsed
from qatrack.qa.models import (
    Category,
    TestList,
    TestListInstance,
    Tolerance,
    UnitTestCollection,
    UnitTestInfo,
)
from qatrack.reports.models import ReportSchedule, SavedReport
from qatrack.service_log.models import (
    ReturnToServiceQA,
    ServiceEvent,
    ServiceEventSchedule,
    ServiceEventTemplate,
    ServiceType,
)
from qatrack.units.models import Modality, Unit


class TestSampleDataGenerator(TestCase):

    def test_generate_small_center(self):
        out = StringIO()
        call_command("generate_sample_data", days=14, clear=True, no_input=True, stdout=out)

        self.assertIn("Successfully generated sample data!", out.getvalue())

        # Units
        self.assertEqual(Unit.objects.count(), 3)
        self.assertTrue(Unit.objects.filter(name__contains="TrueBeam").exists())
        self.assertTrue(Unit.objects.filter(name__contains="Versa").exists())
        self.assertTrue(Unit.objects.filter(name__contains="SOMATOM").exists())

        # QA
        uti = UnitTestInfo.objects.get(unit__name="TB-1 (TrueBeam)", test__slug="laser_x")
        self.assertIsNotNone(uti.reference)
        self.assertIsNotNone(uti.tolerance)

        self.assertGreaterEqual(TestList.objects.count(), 5)
        self.assertGreaterEqual(UnitTestCollection.objects.filter(active=True).count(), 8)
        self.assertGreaterEqual(TestListInstance.objects.count(), 10)
        self.assertEqual(TestListInstance.objects.filter(in_progress=True).count(), 1)

        # Service log & Faults
        self.assertGreaterEqual(ServiceEvent.objects.count(), 3)
        self.assertGreaterEqual(ReturnToServiceQA.objects.count(), 1)
        self.assertGreaterEqual(Fault.objects.count(), 2)
        self.assertGreaterEqual(ServiceEventTemplate.objects.count(), 4)
        self.assertGreaterEqual(ServiceEventSchedule.objects.count(), 2)

        # Parts
        self.assertGreaterEqual(Part.objects.count(), 5)
        self.assertGreaterEqual(PartUsed.objects.count(), 1)

        # Reports
        self.assertGreaterEqual(SavedReport.objects.count(), 4)
        self.assertGreaterEqual(ReportSchedule.objects.count(), 2)

    def test_return_to_service_lists_are_ad_hoc(self):
        """RTS test lists are performed on demand and must not be scheduled."""

        call_command("generate_sample_data", days=1, clear=True, no_input=True, stdout=StringIO())

        rts = UnitTestCollection.objects.filter(name="Linac Return To Service QA")
        self.assertEqual(rts.count(), 2)
        for utc in rts:
            self.assertIsNone(utc.frequency)
            self.assertFalse(utc.auto_schedule)
            self.assertIsNone(utc.due_date)

    def test_negative_days_rejected(self):
        with self.assertRaises(CommandError):
            call_command("generate_sample_data", days=-1, no_input=True, stdout=StringIO())

        self.assertEqual(Unit.objects.count(), 0)

    def test_rerun_without_clear_does_not_collide_on_unit_number(self):
        """Unit.number is unique, so an occupied number must not abort generation."""

        call_command("generate_sample_data", days=1, clear=True, no_input=True, stdout=StringIO())

        # a pre-existing unit now holds number 1, but not the sample unit's name
        Unit.objects.filter(name="TB-1 (TrueBeam)").update(name="Decommissioned Linac")

        call_command("generate_sample_data", days=1, no_input=True, stdout=StringIO())

        self.assertEqual(Unit.objects.filter(name="TB-1 (TrueBeam)").count(), 1)
        self.assertEqual(Unit.objects.count(), 4)
        self.assertEqual(Unit.objects.values("number").distinct().count(), 4)

    def test_rerun_without_clear_does_not_duplicate_data(self):
        """A second run must extend the sample data, not record it all again."""

        call_command("generate_sample_data", days=3, clear=True, no_input=True, stdout=StringIO())

        def counts():
            return {
                "units": Unit.objects.count(),
                "reports": SavedReport.objects.count(),
                "schedules": ReportSchedule.objects.count(),
                "service events": ServiceEvent.objects.count(),
                "test list instances": TestListInstance.objects.count(),
                "faults": Fault.objects.count(),
            }

        before = counts()
        call_command("generate_sample_data", days=3, no_input=True, stdout=StringIO())

        self.assertEqual(before, counts())

    def test_rerun_does_not_overwrite_existing_configuration(self):
        """Units and test infos we did not just create keep their own setup."""

        call_command("generate_sample_data", days=1, clear=True, no_input=True, stdout=StringIO())

        unit = Unit.objects.get(name="TB-1 (TrueBeam)")
        unit.modalities.set([])
        uti = UnitTestInfo.objects.get(unit=unit, test__slug="laser_x")
        other_tolerance = UnitTestInfo.objects.exclude(tolerance=uti.tolerance).exclude(
            tolerance=None).first().tolerance
        uti.tolerance = other_tolerance
        uti.save()

        call_command("generate_sample_data", days=1, no_input=True, stdout=StringIO())

        self.assertEqual(unit.modalities.count(), 0)
        uti.refresh_from_db()
        self.assertEqual(uti.tolerance, other_tolerance)

    def test_existing_user_keeps_its_own_password_and_groups(self):
        """A username we did not create may belong to a real person."""

        existing = User.objects.create_user("admin", "real@example.com", "a-real-password")
        existing.groups.set([Group.objects.create(name="Real Existing Group")])

        call_command("generate_sample_data", days=1, clear=True, no_input=True, stdout=StringIO())

        existing.refresh_from_db()
        self.assertTrue(existing.check_password("a-real-password"))

        groups = set(existing.groups.values_list("name", flat=True))
        self.assertIn("Real Existing Group", groups)  # kept
        self.assertIn("QA Administrators", groups)  # and given the sample role

    def test_linked_user_without_a_password_gets_the_sample_one(self):
        """An account linked elsewhere still has to be usable locally."""

        linked = User.objects.create(username="jane.physicist", email="jane@example.com")
        linked.set_unusable_password()
        linked.save()

        call_command("generate_sample_data", days=1, clear=True, no_input=True, stdout=StringIO())

        linked.refresh_from_db()
        self.assertTrue(linked.check_password("password123"))
        self.assertIn("Medical Physicists", set(linked.groups.values_list("name", flat=True)))

    def test_partially_loaded_default_fixtures(self):
        """Only the fixtures whose own table is empty may be (re)loaded.

        The default fixtures have no primary keys, so reloading the full set
        over rows that are already there fails on their unique names.
        """

        call_command("installfixtures", stdout=StringIO())
        # a default the generator looks up by name, and two it does not
        ServiceType.objects.all().delete()
        Tolerance.objects.all().delete()
        Modality.objects.all().delete()

        call_command("generate_sample_data", days=1, no_input=True, stdout=StringIO())

        self.assertTrue(ServiceType.objects.filter(name="Preventive").exists())
        self.assertEqual(Category.objects.filter(name="Dosimetry").count(), 1)
        self.assertEqual(Unit.objects.count(), 3)

    def test_failed_generation_does_not_leave_database_cleared(self):
        """--clear and generation share a transaction."""

        call_command("generate_sample_data", days=1, clear=True, no_input=True, stdout=StringIO())
        before = TestListInstance.objects.count()
        self.assertGreater(before, 0)

        target = "qatrack.qatrack_core.sample_data.SmallCenterGenerator.generate"
        with mock.patch(target, side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                call_command("generate_sample_data", days=1, clear=True, no_input=True, stdout=StringIO())

        self.assertEqual(Unit.objects.count(), 3)
        self.assertEqual(TestListInstance.objects.count(), before)
