"""
Test module specifically for zoneinfo migration functionality.
Tests all the key areas that were changed from pytz to zoneinfo.
"""
import datetime
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import recurrence
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from qatrack.qa import models
from qatrack.qa.tests import utils as qautils
from qatrack.qatrack_core import dates, scheduling


class TestZoneinfoDateUtilities(TestCase):
    """Test all date utility functions that now use zoneinfo instead of pytz"""

    def setUp(self):
        self.tz = ZoneInfo(settings.TIME_ZONE)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_date_to_datetime_conversion(self):
        """Test date_to_datetime converts dates correctly with zoneinfo"""
        test_date = date(2023, 6, 15)
        result = dates.date_to_datetime(test_date)

        expected_tz = ZoneInfo("America/Toronto")
        expected = timezone.datetime(2023, 6, 15, 0, 0, 0).replace(tzinfo=expected_tz)

        self.assertEqual(result, expected)
        self.assertEqual(result.tzinfo, expected_tz)

    def test_date_to_datetime_passthrough(self):
        """Test date_to_datetime passes through non-date objects"""
        dt = timezone.datetime(2023, 6, 15, 12, 0, 0)
        result = dates.date_to_datetime(dt)
        self.assertEqual(result, dt)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_start_of_day_with_zoneinfo(self):
        """Test start_of_day function with zoneinfo"""
        tz = ZoneInfo("America/Toronto")
        dt = timezone.datetime(2023, 6, 15, 14, 30, 45).replace(tzinfo=tz)

        result = dates.start_of_day(dt)
        expected = timezone.datetime(2023, 6, 15, 0, 0, 0).replace(tzinfo=tz)

        self.assertEqual(result, expected)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_end_of_day_with_zoneinfo(self):
        """Test end_of_day function with zoneinfo"""
        tz = ZoneInfo("America/Toronto")
        dt = timezone.datetime(2023, 6, 15, 14, 30, 45).replace(tzinfo=tz)

        result = dates.end_of_day(dt)
        expected = timezone.datetime(2023, 6, 15, 23, 59, 59, 999999).replace(tzinfo=tz)

        self.assertEqual(result, expected)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_start_end_of_day_naive(self):
        """Test start/end of day with naive=True parameter"""
        dt = timezone.datetime(2023, 6, 15, 14, 30, 45)

        start_result = dates.start_of_day(dt, naive=True)
        end_result = dates.end_of_day(dt, naive=True)

        expected_start = timezone.datetime(2023, 6, 15, 0, 0, 0)
        expected_end = timezone.datetime(2023, 6, 15, 23, 59, 59, 999999)

        self.assertEqual(start_result, expected_start)
        self.assertEqual(end_result, expected_end)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_month_start_and_end_with_zoneinfo(self):
        """Test month_start_and_end function with zoneinfo"""
        start, end = dates.month_start_and_end(2023, 6)

        tz = ZoneInfo("America/Toronto")
        expected_start = timezone.datetime(2023, 6, 1).replace(tzinfo=tz)
        expected_end = timezone.datetime(2023, 6, 30).replace(tzinfo=tz)

        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_local_start_of_day(self):
        """Test local_start_of_day function"""
        tz = ZoneInfo("America/Toronto")
        dt = timezone.datetime(2023, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)

        result = dates.local_start_of_day(dt)
        # Should convert to local timezone and get start of day
        expected = dt.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)

        self.assertEqual(result, expected)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_local_end_of_day(self):
        """Test local_end_of_day function"""
        tz = ZoneInfo("America/Toronto")
        dt = timezone.datetime(2023, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)

        result = dates.local_end_of_day(dt)
        # Should convert to local timezone and get end of day
        expected = dt.astimezone(tz).replace(hour=23, minute=59, second=59, microsecond=999999)

        self.assertEqual(result, expected)


class TestZoneinfoSchedulingFunctions(TestCase):
    """Test scheduling functions that were updated to use zoneinfo"""

    def setUp(self):
        self.tz = ZoneInfo(settings.TIME_ZONE)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_calc_due_date_with_zoneinfo(self):
        """Test calc_due_date function properly handles zoneinfo timezones"""
        frequency = qautils.create_frequency(name="daily", slug="daily", interval=1)

        tz = ZoneInfo("America/Toronto")
        completed = timezone.datetime(2023, 6, 15, 10, 0).replace(tzinfo=tz)
        due = timezone.datetime(2023, 6, 15, 23, 59, 59).replace(tzinfo=tz)

        next_due = scheduling.calc_due_date(completed, due, frequency)

        # Should calculate next occurrence correctly
        self.assertIsNotNone(next_due)
        self.assertEqual(next_due.tzinfo, tz)

    @override_settings(TIME_ZONE="Australia/Melbourne")
    def test_calc_due_date_different_timezone(self):
        """Test calc_due_date works correctly in different timezone"""
        frequency = qautils.create_frequency(name="weekly", slug="weekly", interval=7)

        tz = ZoneInfo("Australia/Melbourne")
        completed = timezone.datetime(2023, 6, 15, 10, 0).replace(tzinfo=tz)
        due = timezone.datetime(2023, 6, 15, 23, 59, 59).replace(tzinfo=tz)

        next_due = scheduling.calc_due_date(completed, due, frequency)

        self.assertIsNotNone(next_due)
        self.assertEqual(next_due.tzinfo, tz)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_calc_due_date_dst_transition(self):
        """Test calc_due_date handles DST transitions correctly with zoneinfo"""
        frequency = qautils.create_frequency(name="daily", slug="daily", interval=1)

        tz = ZoneInfo("America/Toronto")
        # Test around spring DST transition (second Sunday in March)
        completed = timezone.datetime(2023, 3, 12, 10, 0).replace(tzinfo=tz)
        due = timezone.datetime(2023, 3, 12, 23, 59, 59).replace(tzinfo=tz)

        next_due = scheduling.calc_due_date(completed, due, frequency)

        self.assertIsNotNone(next_due)
        self.assertEqual(next_due.tzinfo, tz)
        # Should be the next day despite DST transition
        self.assertEqual(next_due.date(), completed.date() + timedelta(days=1))

    @override_settings(TIME_ZONE="America/Toronto")
    def test_string_assignment_compatibility(self):
        """Test the new string assignment compatibility logic"""
        # Create a frequency and manually set the _from_string_assignment flag
        frequency = qautils.create_frequency()
        frequency.recurrences._from_string_assignment = True

        tz = ZoneInfo("America/Toronto")
        completed = timezone.datetime(2023, 6, 15, 10, 0).replace(tzinfo=tz)
        due = timezone.datetime(2023, 6, 15, 23, 59, 59).replace(tzinfo=tz)

        # Should use the special string assignment logic
        next_due = scheduling.calc_due_date(completed, due, frequency)

        self.assertIsNotNone(next_due)
        self.assertEqual(next_due.tzinfo, tz)

    def test_qc_window_with_zoneinfo(self):
        """Test qc_window function works with zoneinfo"""
        frequency = qautils.create_frequency()
        frequency.window_start = 1
        frequency.window_end = 2

        tz = ZoneInfo(settings.TIME_ZONE)
        due_date = timezone.datetime(2023, 6, 15, 12, 0).replace(tzinfo=tz)

        start, end = scheduling.qc_window(due_date, frequency)

        self.assertIsNotNone(start)
        self.assertIsNotNone(end)
        self.assertEqual(start.tzinfo, tz)
        self.assertEqual(end.tzinfo, tz)


class TestRecurrenceStringAssignment(TestCase):
    """Test the custom __setattr__ method that handles recurrence string assignments"""

    def setUp(self):
        self.tz = ZoneInfo(settings.TIME_ZONE)

    def test_string_assignment_to_recurrences(self):
        """Test that string assignments to recurrences field are handled correctly"""
        frequency = models.Frequency(name="test", slug="test")

        # This should trigger the custom __setattr__ method
        frequency.recurrences = "FREQ=DAILY;INTERVAL=1"

        # Should have been converted to a proper recurrence object
        self.assertIsNotNone(frequency.recurrences)
        self.assertTrue(hasattr(frequency.recurrences, 'dtstart'))
        self.assertEqual(frequency.recurrences.dtstart.tzinfo, self.tz)

    def test_string_assignment_with_rrule_prefix(self):
        """Test string assignment with RRULE: prefix"""
        frequency = models.Frequency(name="test", slug="test")

        frequency.recurrences = "RRULE:FREQ=WEEKLY;INTERVAL=2"

        self.assertIsNotNone(frequency.recurrences)
        self.assertTrue(hasattr(frequency.recurrences, 'dtstart'))
        self.assertEqual(frequency.recurrences.dtstart.tzinfo, self.tz)

    def test_recurrence_object_assignment(self):
        """Test that actual recurrence objects are not modified"""
        frequency = models.Frequency(name="test", slug="test")

        # Create a proper recurrence object
        rule = recurrence.Rule(freq=recurrence.DAILY, interval=1)
        rec = recurrence.Recurrence(rrules=[rule], dtstart=timezone.datetime(2023, 1, 1).replace(tzinfo=self.tz))

        # This should NOT trigger the string handling logic
        frequency.recurrences = rec

        self.assertEqual(frequency.recurrences, rec)

    def test_empty_string_assignment(self):
        """Test that empty strings bypass our custom conversion and use field default behavior"""
        frequency = models.Frequency(name="test", slug="test")

        frequency.recurrences = ""

        # Empty strings bypass our custom __setattr__ logic (due to value.strip() check)
        # The RecurrenceField itself creates a default recurrence object when assigned ""
        # This is the field's default behavior, not our custom conversion
        self.assertIsNotNone(frequency.recurrences)
        self.assertTrue(hasattr(frequency.recurrences, 'dtstart'))

    def test_non_recurrence_field_assignment(self):
        """Test that assignments to other fields are not affected"""
        frequency = models.Frequency(name="test", slug="test")

        # Normal field assignment should work normally
        frequency.name = "new_name"

        self.assertEqual(frequency.name, "new_name")


class TestCrossTimezoneCompatibility(TestCase):
    """Test that the zoneinfo implementation works across different timezones"""

    def test_multiple_timezones(self):
        """Test that functions work correctly in different timezone settings"""
        timezones_to_test = [
            "America/Toronto",
            "America/Los_Angeles",
            "Europe/London",
            "Australia/Melbourne",
            "Asia/Tokyo",
        ]

        for tz_name in timezones_to_test:
            with override_settings(TIME_ZONE=tz_name):
                with self.subTest(timezone=tz_name):
                    tz = ZoneInfo(tz_name)

                    # Test basic date operations
                    test_date = date(2023, 6, 15)
                    result = dates.date_to_datetime(test_date)
                    self.assertEqual(result.tzinfo, tz)

                    # Test start/end of day
                    dt = timezone.datetime(2023, 6, 15, 14, 30).replace(tzinfo=tz)
                    start = dates.start_of_day(dt)
                    end = dates.end_of_day(dt)

                    self.assertEqual(start.tzinfo, tz)
                    self.assertEqual(end.tzinfo, tz)
                    self.assertEqual(start.hour, 0)
                    self.assertEqual(end.hour, 23)

    @override_settings(TIME_ZONE="America/Toronto")
    def test_utc_conversion_consistency(self):
        """Test that UTC conversions are consistent with zoneinfo"""
        tz = ZoneInfo("America/Toronto")

        # Create a datetime in local timezone
        local_dt = timezone.datetime(2023, 6, 15, 14, 30).replace(tzinfo=tz)

        # Convert to UTC and back
        utc_dt = local_dt.astimezone(datetime.UTC)
        back_to_local = utc_dt.astimezone(tz)

        self.assertEqual(local_dt, back_to_local)


class TestMigrationCompatibility(TestCase):
    """Test that existing data works correctly with the new zoneinfo implementation"""

    def test_existing_frequency_objects(self):
        """Test that existing frequency objects work with zoneinfo"""
        # Create a frequency object (simulating existing data)
        frequency = qautils.create_frequency()

        # Should have proper zoneinfo timezone
        self.assertIsInstance(frequency.recurrences.dtstart.tzinfo, ZoneInfo)

        # Should work with scheduling functions
        tz = ZoneInfo(settings.TIME_ZONE)
        completed = timezone.datetime(2023, 6, 15, 10, 0).replace(tzinfo=tz)
        due = timezone.datetime(2023, 6, 15, 23, 59, 59).replace(tzinfo=tz)

        next_due = scheduling.calc_due_date(completed, due, frequency)
        self.assertIsNotNone(next_due)

    def test_relocalize_recurrences(self):
        """Test the relocalize_recurrences functionality"""
        # Create a frequency
        frequency = qautils.create_frequency()
        old_dtstart = frequency.recurrences.dtstart

        # Change timezone setting and relocalize
        with override_settings(TIME_ZONE="America/Los_Angeles"):
            frequency.relocalize_recurrence()
            new_dtstart = frequency.recurrences.dtstart

            # Should have new timezone
            self.assertEqual(new_dtstart.tzinfo, ZoneInfo("America/Los_Angeles"))
            # But same logical time
            self.assertEqual(new_dtstart.replace(tzinfo=None), old_dtstart.replace(tzinfo=None))


class TestZoneinfoEdgeCases(TestCase):
    """Test edge cases and potential failure points with zoneinfo"""

    @override_settings(TIME_ZONE="America/Toronto")
    def test_dst_spring_forward(self):
        """Test behavior during spring DST transition (spring forward)"""
        tz = ZoneInfo("America/Toronto")

        # 2023 DST starts March 12, 2:00 AM -> 3:00 AM
        # Test scheduling around this time
        frequency = qautils.create_frequency(name="hourly", slug="hourly", interval=1)

        # Time just before DST transition
        completed = timezone.datetime(2023, 3, 12, 1, 30).replace(tzinfo=tz)
        due = timezone.datetime(2023, 3, 12, 2, 30).replace(tzinfo=tz)

        # Should handle the transition gracefully
        try:
            next_due = scheduling.calc_due_date(completed, due, frequency)
            self.assertIsNotNone(next_due)
        except Exception as e:
            self.fail(f"DST transition caused error: {e}")

    @override_settings(TIME_ZONE="America/Toronto")
    def test_dst_fall_back(self):
        """Test behavior during fall DST transition (fall back)"""
        tz = ZoneInfo("America/Toronto")

        # 2023 DST ends November 5, 2:00 AM -> 1:00 AM
        frequency = qautils.create_frequency(name="hourly", slug="hourly", interval=1)

        # Time during the "repeated" hour
        completed = timezone.datetime(2023, 11, 5, 1, 30).replace(tzinfo=tz)
        due = timezone.datetime(2023, 11, 5, 2, 30).replace(tzinfo=tz)

        # Should handle the transition gracefully
        try:
            next_due = scheduling.calc_due_date(completed, due, frequency)
            self.assertIsNotNone(next_due)
        except Exception as e:
            self.fail(f"DST transition caused error: {e}")

    def test_invalid_timezone_handling(self):
        """Test that invalid timezones are handled gracefully"""
        with self.assertRaises(ZoneInfoNotFoundError):
            ZoneInfo("Invalid/Timezone")

    def test_boundary_conditions(self):
        """Test boundary conditions for date calculations"""
        tz = ZoneInfo(settings.TIME_ZONE)

        # Test leap year boundary
        leap_year_dt = timezone.datetime(2024, 2, 29, 12, 0).replace(tzinfo=tz)
        start = dates.start_of_day(leap_year_dt)
        end = dates.end_of_day(leap_year_dt)

        self.assertEqual(start.day, 29)
        self.assertEqual(end.day, 29)

        # Test year boundary
        year_end = timezone.datetime(2023, 12, 31, 23, 59, 59).replace(tzinfo=tz)
        next_day_start = dates.start_of_day(year_end + timedelta(days=1))

        self.assertEqual(next_day_start.year, 2024)
        self.assertEqual(next_day_start.month, 1)
        self.assertEqual(next_day_start.day, 1)


# Import the exception for the test
try:
    from zoneinfo import ZoneInfoNotFoundError
except ImportError:
    # For older Python versions
    class ZoneInfoNotFoundError(Exception):
        pass
