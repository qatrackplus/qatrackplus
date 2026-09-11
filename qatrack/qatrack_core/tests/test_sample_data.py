from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from qatrack.faults.models import Fault
from qatrack.parts.models import Part, PartUsed
from qatrack.qa.models import TestList, TestListInstance, UnitTestCollection
from qatrack.reports.models import ReportSchedule, SavedReport
from qatrack.service_log.models import (
    ReturnToServiceQA,
    ServiceEvent,
    ServiceEventSchedule,
    ServiceEventTemplate,
)
from qatrack.units.models import Unit


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
