from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
import pytz
import recurrence

from qatrack.qa import models
from qatrack.qa.tests import utils as qautils
from qatrack.qatrack_core import dates, scheduling


class TestDateFunctions:

    def test_last_month_dates_jan(self):
        dt = timezone.datetime(2019, 1, 15, tzinfo=timezone.utc)
        start, end = dates.last_month_dates(dt)
        tz = timezone.get_current_timezone()
        assert start == tz.localize(timezone.datetime(2018, 12, 1))
        assert end == tz.localize(timezone.datetime(2018, 12, 31))

    def test_last_month_dates_dec(self):
        dt = timezone.datetime(2019, 12, 15, tzinfo=timezone.utc)
        start, end = dates.last_month_dates(dt)
        tz = timezone.get_current_timezone()
        assert start == tz.localize(timezone.datetime(2019, 11, 1))
        assert end == tz.localize(timezone.datetime(2019, 11, 30))


class TestCalcDueDate(TestCase):

    def setUp(self):
        self.tz = pytz.timezone("America/Toronto")

    def make_dt(self, dt, tz=pytz.timezone("America/Toronto")):
        """return a tz localized datetime from dt"""
        return tz.localize(dt)

    @property
    def mwf(self):
        """Generate a MWF frequency with a 0 day window_start and 1 day window_end"""
        rule = recurrence.Rule(
            freq=recurrence.WEEKLY,
            byday=[recurrence.MO, recurrence.WE, recurrence.FR],
        )
        return models.Frequency(
            name="MWF",
            slug="mwf",
            recurrences=recurrence.Recurrence(
                rrules=[rule],
                dtstart=timezone.datetime(2012, 1, 1, tzinfo=timezone.utc),
            ),
            window_start=0,
            window_end=1,
        )

    @property
    def wed(self):
        """Generate a Wednesday of week frequency with a 1 day window_start (so
        Tues or Wed should work) and 1 day window_end"""

        rule = recurrence.Rule(
            freq=recurrence.WEEKLY,
            byday=[recurrence.WE],
        )
        return models.Frequency(
            name="Wed",
            slug="wed",
            recurrences=recurrence.Recurrence(
                rrules=[rule],
                dtstart=timezone.datetime(2012, 1, 1, tzinfo=timezone.utc),
            ),
            window_end=1,
            window_start=1,
        )

    def day_of_month(self, day=1):
        """Generate a frequency to be performed on the specific day of month
        with a 7 day window_start and 7 day window_end"""

        rule = recurrence.Rule(freq=recurrence.MONTHLY, bymonthday=day)
        return models.Frequency(
            name="Day of Month",
            slug="day-of-month",
            recurrences=recurrence.Recurrence(
                rrules=[rule],
                dtstart=timezone.datetime(2012, 1, 1, tzinfo=timezone.utc),
            ),
            window_end=7,
            window_start=7,
        )

    def n_weekly(self, weeks=4):
        """Generate a frequency to be performed on the specific day of month
        with a 7 day window_start and 7 day window_end"""

        rule = recurrence.Rule(freq=recurrence.WEEKLY, interval=weeks)
        return models.Frequency(
            name="%s weekly" % weeks,
            slug="%s-weekly" % weeks,
            recurrences=recurrence.Recurrence(
                rrules=[rule],
                dtstart=timezone.datetime(2012, 1, 1, tzinfo=timezone.utc),
            ),
            window_end=7,
            window_start=7,
        )

    def test_adhoc(self):
        """Null frequency should result in a null due date"""
        assert scheduling.calc_due_date(timezone.now(), timezone.now(), None) is None

    def test_daily_offset_due_today_before_due_time(self):
        """Daily frequency when performed today should result in due date one day in future"""
        daily = qautils.create_frequency(name="d", slug="d", interval=1, save=False)
        six_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 6, 0))
        due = six_am_today + timezone.timedelta(hours=1)
        six_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 6, 0))
        assert scheduling.calc_due_date(six_am_today, due, daily).date() == six_am_tmrw.date()

    def test_daily_offset_due_today_after_due_time(self):
        """Daily frequency when performed today should result in due date one day in future"""
        daily = qautils.create_frequency(name="d", slug="d", interval=1, save=False)
        eight_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 8, 0))
        due = eight_am_today - timezone.timedelta(hours=1)
        eight_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 8, 0))
        assert scheduling.calc_due_date(eight_am_today, due, daily).date() == eight_am_tmrw.date()

    def test_daily_offset_due_today_equal_due_time(self):
        """Daily frequency when performed today should result in due date one day in future"""
        daily = qautils.create_frequency(name="d", slug="d", interval=1, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due = seven_am_today
        seven_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert scheduling.calc_due_date(seven_am_today, due, daily).date() == seven_am_tmrw.date()

    def test_daily_offset_due_yesterday(self):
        """Daily frequency when performed today should result in due date one day in future"""
        daily = qautils.create_frequency(name="d", slug="d", interval=1, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due = self.make_dt(timezone.datetime(2018, 11, 19, 7, 0))
        seven_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert scheduling.calc_due_date(seven_am_today, due, daily).date() == seven_am_tmrw.date()

    def test_daily_offset_due_tomorrow(self):
        daily = qautils.create_frequency(name="d", slug="d", interval=1, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        seven_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert scheduling.calc_due_date(seven_am_today, seven_am_tmrw, daily).date() == seven_am_tmrw.date()

    def test_monthly_offset(self):
        """Monthly frequency when performed today should result in due date 28 days in future"""
        monthly = qautils.create_frequency(name="d", slug="d", interval=28, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due_date = timezone.now()  # arbitrary
        seven_am_4wks = self.make_dt(timezone.datetime(2018, 12, 18, 7, 0))
        assert scheduling.calc_due_date(seven_am_today, due_date, monthly).date() == seven_am_4wks.date()

    def test_annual_offset(self):
        """Annual frequency when performed today should result in due date 300 days in future"""
        annual = qautils.create_frequency(name="d", slug="d", interval=300, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 12, 20, 7, 0))  # arbitrary
        seven_am_300_days = self.make_dt(timezone.datetime(2019, 9, 16, 7, 0))
        assert scheduling.calc_due_date(seven_am_today, due_date, annual).date() == seven_am_300_days.date()

    def test_mwf_perf_monday_before_due_time(self):
        """With a MWF test performed at 6am on a Monday, if the due date is 7 am, the due date should be set to Wed"""
        six_am_monday = self.make_dt(timezone.datetime(2018, 11, 19, 6, 0))
        seven_am_monday = self.make_dt(timezone.datetime(2018, 11, 19, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert scheduling.calc_due_date(six_am_monday, seven_am_monday, self.mwf) == expected_due_date

    def test_mwf_perf_monday_after_due_time(self):
        """With a MWF test performed at 8am on a Monday, if the due date is 7 am, the due date should be set to Wed"""
        seven_am_monday = self.make_dt(timezone.datetime(2018, 11, 19, 7, 0))
        eight_am_monday = self.make_dt(timezone.datetime(2018, 11, 19, 8, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert scheduling.calc_due_date(eight_am_monday, seven_am_monday, self.mwf) == expected_due_date

    def test_mwf_perf_tuesday(self):
        """With a MWF test performed on a Tuesday with a due date of Wed, the due date should be set to Wed"""
        seven_am_tues = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        seven_am_wed = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        expected_due_date = seven_am_wed
        assert scheduling.calc_due_date(seven_am_tues, seven_am_wed, self.mwf) == expected_due_date

    def test_mwf_due_monday_perf_sat(self):
        """With a MWF test due Mon, performed on a Sat, the due date should be set to Mon"""
        seven_am_sat = self.make_dt(timezone.datetime(2018, 11, 24, 7, 0))
        seven_am_mon = self.make_dt(timezone.datetime(2018, 11, 26, 7, 0))
        expected_due_date = seven_am_mon
        assert scheduling.calc_due_date(seven_am_sat, seven_am_mon, self.mwf) == expected_due_date

    def test_mwf_due_monday_perf_sat_after(self):
        """With a MWF test due Mon, performed on a Sat after, the due date should be set to Mon next"""
        seven_am_sat_next = self.make_dt(timezone.datetime(2020, 5, 16, 7, 0))
        seven_am_mon = self.make_dt(timezone.datetime(2020, 5, 11, 7, 0))
        seven_am_mon_next = self.make_dt(timezone.datetime(2020, 5, 18, 7, 0))
        expected_due_date = seven_am_mon_next
        assert scheduling.calc_due_date(seven_am_sat_next, seven_am_mon, self.mwf) == expected_due_date

    def test_mwf_due_friday_perf_sat(self):
        """With a MWF test due Friday performed on a Sat, the due date should be set to Mon"""
        seven_am_fri = self.make_dt(timezone.datetime(2018, 11, 23, 7, 0))
        seven_am_sat = self.make_dt(timezone.datetime(2018, 11, 24, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 11, 26, 7, 0))
        assert scheduling.calc_due_date(seven_am_sat, seven_am_fri, self.mwf) == expected_due_date

    def test_first_of_month_before_window(self):
        """With a first of month test performed in the middle of the month, the
        due date should unchanged"""
        today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        expected_due_date = due_date
        assert scheduling.calc_due_date(today, due_date, self.day_of_month(1)) == expected_due_date

    def test_first_of_month_in_window_before(self):
        """With a first of month test performed in the middle of the month, the
        due date should unchanged"""
        today = self.make_dt(timezone.datetime(2018, 11, 29, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        next_month = self.make_dt(timezone.datetime(2019, 1, 1, 7, 0))
        assert scheduling.calc_due_date(today, due_date, self.day_of_month(1)) == next_month

    def test_first_of_month_performed_first_of_month(self):
        """With a first of month test performed on the first of the month, the
        due date should be set to first of next month"""
        today = self.make_dt(timezone.datetime(2018, 11, 1, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 11, 1, 7, 0))
        next_month = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        assert scheduling.calc_due_date(today, due_date, self.day_of_month(1)).date() == next_month.date()

    def test_first_of_month_performed_after_first_of_month(self):
        """With a first of month test performed on the second of the month, the
        due date should be set to first of next month"""
        first_of_month = self.make_dt(timezone.datetime(2018, 11, 1, 7, 0))
        today = self.make_dt(timezone.datetime(2018, 11, 2, 7, 0))
        next_month = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        assert scheduling.calc_due_date(today, first_of_month, self.day_of_month(1)).date() == next_month.date()

    def test_first_of_month_performed_day_before(self):
        """If a Test List is performed on e.g. the 31st, the due date should
        be advanced to the next month, not the next day"""
        today = self.make_dt(timezone.datetime(2018, 11, 30, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2019, 1, 1, 7, 0))
        assert scheduling.calc_due_date(today, due_date, self.day_of_month(1)).date() == expected_due_date.date()

    def test_wed_of_week_performed_mon(self):
        """If a Test List is due every Wed and performed on a Mon, the due date should be
        advanced 2 days forward, not the next day (obviously depends on config or frequency!)
        """
        mon = self.make_dt(timezone.datetime(2018, 11, 26, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 11, 28, 7, 0))
        assert scheduling.calc_due_date(mon, due_date, self.wed).date() == due_date.date()

    def test_wed_of_week_performed_tues(self):
        """If a Test List is due every Wed and performed on a Tues, the due date should be
        advanced 8 days forward, not the next day
        """
        tue = self.make_dt(timezone.datetime(2018, 11, 27, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 11, 28, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 5, 7, 0))
        assert scheduling.calc_due_date(tue, due_date, self.wed).date() == expected_due_date.date()

    def test_wed_of_week_performed_wed(self):
        """If a Test List is due every Wed and performed on a Wed, the due date should be
        advanced 7 days forward
        """
        wed = self.make_dt(timezone.datetime(2018, 11, 28, 7, 0))
        due_date = wed
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 5, 7, 0))
        assert scheduling.calc_due_date(wed, due_date, self.wed).date() == expected_due_date.date()

    def test_wed_of_week_performed_thurs(self):
        """If a Test List is due every Wed and performed on a Wed, the due date should be
        advanced 7 days forward
        """
        thu = self.make_dt(timezone.datetime(2018, 11, 29, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 11, 28, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 5, 7, 0))
        assert scheduling.calc_due_date(thu, due_date, self.wed).date() == expected_due_date.date()

    def test_first_of_month_performed_long_after_outside_next_window(self):
        """If a test list is due on say Apr 1st and is not performed until Nov 20
        the due date should be updated to Dec 1st"""

        today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 4, 1, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        assert scheduling.calc_due_date(today, due_date, self.day_of_month(1)).date() == expected_due_date.date()

    def test_first_of_month_performed_long_after_inside_next_window(self):
        """If a test list is due on say Apr 1st and is not performed until Nov 27
        the due date should be updated to Jan 1st"""

        today = self.make_dt(timezone.datetime(2018, 11, 27, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 4, 1, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2019, 1, 1, 7, 0))
        assert scheduling.calc_due_date(today, due_date, self.day_of_month(1)).date() == expected_due_date.date()

    def test_first_of_month_performed_long_after_past_next_window(self):
        """If a test list is due on say Apr 1st and is not performed until Dec 2
        the due date should be updated to Jan 1st"""

        today = self.make_dt(timezone.datetime(2018, 12, 2, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 4, 1, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2019, 1, 1, 7, 0))
        assert scheduling.calc_due_date(today, due_date, self.day_of_month(1)).date() == expected_due_date.date()

    def test_4_weekly_performed_long_after_outside_next_window(self):
        """If a test list is due on say Apr 1st and is not performed until Nov 20
        the due date should be updated to Dec 1st"""

        today = self.make_dt(timezone.datetime(2018, 11, 1, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 4, 15, 7, 0))
        # due date in Nov is 8 4 week periods after April 15 which is Nov 25
        expected_due_date = self.make_dt(timezone.datetime(2018, 11, 25, 7, 0))
        assert scheduling.calc_due_date(today, due_date, self.n_weekly(4)).date() == expected_due_date.date()

    def test_4_weekly_long_after_inside_next_window(self):
        """If a test list is due on say Apr 1st and is not performed until Nov 27
        the due date should be updated to Jan 1st"""

        today = self.make_dt(timezone.datetime(2018, 11, 23, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 4, 15, 7, 0))
        # due date in Nov is 8 4 week periods after April 15 which is Nov 25
        # due date in Dec is 9 4 week periods after April 15 which is Dec 23
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 23, 7, 0))
        assert scheduling.calc_due_date(today, due_date, self.n_weekly(4)).date() == expected_due_date.date()

    def test_first_of_month_performed_long_after_past_next_window_2(self):
        """If a test list is due on say Apr 15th and is not performed until Nov 26
        the due date should be updated to Dec 23"""

        today = self.make_dt(timezone.datetime(2018, 11, 26, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 4, 15, 7, 0))
        # due date in Nov is 8 4 week periods after April 15 which is Nov 25
        # due date in Dec is 9 4 week periods after April 15 which is Dec 23
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 23, 7, 0))
        assert scheduling.calc_due_date(today, due_date, self.n_weekly(4)).date() == expected_due_date.date()

    def test_first_of_month_performed_long_after_past_next_window_2(self):
        """If a test list is due on say Apr 15th and is not performed until Nov 26
        the due date should be updated to Dec 23"""

        today = self.make_dt(timezone.datetime(2018, 11, 26, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 4, 15, 7, 0))
        # due date in Nov is 8 4 week periods after April 15 which is Nov 25
        # due date in Dec is 9 4 week periods after April 15 which is Dec 23
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 23, 7, 0))
        assert (
            scheduling.calc_due_date(today, due_date, self.n_weekly(4)).date()
            == expected_due_date.date()
        )

    def test_first_of_month_us_classical_offset(self):
        """Ensure due date is calculated correctly when the UTC date is ahead
        of the local date.  See RAM-2297."""
        work_completed = timezone.datetime(2023, 1, 11, 0, 5, 0, tzinfo=timezone.utc)
        previous_due_date = timezone.datetime(
            2023, 1, 1, 22, 15, 30, tzinfo=timezone.utc
        )
        first_of_month = self.day_of_month(day=1)
        first_of_month.window_start = None
        first_of_month.save()
        due_date = scheduling.calc_due_date(
            work_completed, previous_due_date, first_of_month
        )
        expected_due_date = timezone.datetime(2023, 2, 1).date()
        assert due_date.astimezone(self.tz).date() == expected_due_date

    def test_first_of_month_australia_classical_offset(self):
        """Ensure due date is calculated correctly when the UTC date is prior
        to the local date.  See RAM-2297."""
        with override_settings(TIME_ZONE="Australia/Melbourne"):
            tz = pytz.timezone("Australia/Melbourne")
            work_completed = timezone.datetime(2023, 1, 11, 14, 5, 0, tzinfo=timezone.utc)
            previous_due_date = timezone.datetime(
                2023, 1, 1, 22, 15, 30, tzinfo=timezone.utc
            )
            first_of_month = self.day_of_month(day=1)
            first_of_month.window_start = None
            first_of_month.save()
            due_date = scheduling.calc_due_date(
                work_completed, previous_due_date, first_of_month
            )
            expected_due_date = timezone.datetime(2023, 2, 1).date()
            assert due_date.astimezone(tz).date() == expected_due_date

    def test_first_of_month_us(self):
        """Ensure due date is calculated correctly when the UTC date is ahead
        of the local date.  See RAM-2297."""
        work_completed = timezone.datetime(2023, 1, 11, 0, 5, 0, tzinfo=timezone.utc)
        previous_due_date = timezone.datetime(
            2023, 1, 1, 2, 15, 30, tzinfo=timezone.utc
        )
        first_of_month = self.day_of_month(day=1)
        due_date = scheduling.calc_due_date(
            work_completed, previous_due_date, first_of_month
        )
        expected_due_date = timezone.datetime(2023, 2, 1).date()
        assert due_date.astimezone(self.tz).date() == expected_due_date

    def test_first_of_month_australia(self):
        """Ensure due date is calculated correctly when the UTC date is prior
        to the local date.  See RAM-2297."""
        with override_settings(TIME_ZONE="Australia/Melbourne"):
            tz = pytz.timezone("Australia/Melbourne")
            work_completed = timezone.datetime(2023, 1, 11, 14, 5, 0, tzinfo=timezone.utc)
            previous_due_date = timezone.datetime(
                2023, 1, 1, 22, 15, 30, tzinfo=timezone.utc
            )
            first_of_month = self.day_of_month(day=1)
            due_date = scheduling.calc_due_date(
                work_completed, previous_due_date, first_of_month
            )
            expected_due_date = timezone.datetime(2023, 2, 1).date()
            assert due_date.astimezone(tz).date() == expected_due_date



class TestRelocalizeRecurrences(TestCase):

    def test_find_models_with_recurrence(self):
        models = scheduling.RecurrenceFieldMixin.recurrence_models()
        assert len(models) == 7  # ReportSchedule, Frequency, 5 notice types

    def test_relocalize(self):
        f = qautils.create_frequency()
        assert 'DTSTART:20120101T05' in str(f.recurrences)  # starts in US/Eastern
        with override_settings(TIME_ZONE="US/Pacific"):
            scheduling.RecurrenceFieldMixin.relocalize_recurrences()
            f.refresh_from_db()
            assert 'DTSTART:20120101T08' in str(f.recurrences)  # should now be in US/Pacific
