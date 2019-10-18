import io
import json

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
import pytz
import recurrence

from qatrack.qa import models, testpack
from qatrack.qa import utils as qautils
from qatrack.qa.tests import utils


class TestUtils(TestCase):

    def test_unique(self):
        items = ["foo", "foo", "bar"]
        self.assertListEqual(items[1:], qautils.unique(items))

    def test_almost_equal_none(self):
        self.assertFalse(qautils.almost_equal(None, None))

    def test_almost_equal_equal(self):
        self.assertTrue(qautils.almost_equal(1, 1))

    def test_almost_equal_small(self):
        self.assertTrue(qautils.almost_equal(1, 1 + 1E-10))

    def test_almost_equal_zero(self):
        self.assertTrue(qautils.almost_equal(0, 0))

    def test_tokenize(self):
        proc = "result = a + 2"
        self.assertListEqual(proc.split(), qautils.tokenize_composite_calc(proc))

    def test_set_encoder_set(self):
        self.assertIsInstance(json.dumps(set([1, 2]), cls=qautils.SetEncoder), str)

    def test_float_format(self):
        numbers = (
            (0.999, 3, "0.999"),
            (-0.999, 3, "-0.999"),
            (0.999, 1, "1"),
            (0.999, 2, "1.0"),
            (0.0, 4, "0"),
            (-0.0, 4, "0"),
            (1234.567, 1, "1e+3"),
            (1234.567, 2, "1.2e+3"),
            (1234.567, 5, "1234.6"),
        )

        for number, prec, expected in numbers:
            self.assertEqual(qautils.to_precision(number, prec), expected)


class TestImportExport(TestCase):

    def setUp(self):

        self.user = utils.create_user()
        self.tl1 = utils.create_test_list("tl1 é")
        self.tl2 = utils.create_test_list("tl2")
        self.tl3 = utils.create_test_list("tl3")
        self.tlc = utils.create_cycle([self.tl1, self.tl2])
        self.t1 = utils.create_test("t1")
        self.t2 = utils.create_test("t2")
        self.t3 = utils.create_test("t3")
        self.t4 = utils.create_test("t4")
        utils.create_test_list_membership(self.tl1, self.t1)
        utils.create_test_list_membership(self.tl2, self.t2)
        utils.create_test_list_membership(self.tl3, self.t3)

        self.tlqs = models.TestList.objects.filter(pk=self.tl3.pk)
        self.tlcqs = models.TestListCycle.objects.filter(pk=self.tlc.pk)
        self.extra = models.Test.objects.filter(pk=self.t4.pk)

    def test_round_trip(self):
        pack = json.dumps(testpack.create_testpack(
            test_lists=self.tlqs,
            cycles=self.tlcqs,
            extra_tests=self.extra,
        ))
        models.TestListCycle.objects.all().delete()
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        models.Category.objects.all().delete()
        testpack.add_testpack(pack)

        assert models.Test.objects.count() == 4
        assert models.TestList.objects.count() == 3
        assert models.TestListMembership.objects.count() == 3
        assert models.TestListCycle.objects.count() == 1
        assert models.TestListCycleMembership.objects.count() == 2

    def test_create_pack(self):

        pack = testpack.create_testpack(self.tlqs, self.tlcqs)

        assert 'meta' in pack
        assert 'objects' in pack

        test_found = False
        list_found = False
        for tl_dat in pack['objects']['testlists']:
            tl = json.loads(tl_dat)
            if tl['object']['fields']['name'] == self.tl3.name:
                list_found = True

            for o in tl['dependencies']:
                try:
                    if o['fields']['name'] == self.t3.name:
                        test_found = True
                except KeyError:
                    pass

        assert list_found and test_found

    def test_save_pack(self):
        pack = testpack.create_testpack(self.tlqs, self.tlcqs)
        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        # check the accented character in test list 1 name was written
        assert "\\u00e9" in fp.read()

    def test_non_destructive_load(self):
        ntl = models.TestList.objects.count()
        nt = models.Test.objects.count()
        pack = testpack.create_testpack(self.tlqs, self.tlcqs, self.extra)
        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(fp)
        assert models.TestList.objects.count() == 2 * ntl
        assert models.Test.objects.count() == 2 * nt

    def test_load(self):
        pack = testpack.create_testpack(self.tlqs, self.tlcqs)
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        models.TestListCycle.objects.all().delete()

        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(fp)

        assert models.TestList.objects.filter(name=self.tl1.name).exists()
        assert models.Test.objects.filter(name=self.t1.name).exists()
        assert models.TestListCycle.objects.filter(name=self.tlc.name).exists()
        assert self.tl1.name in models.TestListCycle.objects.values_list("test_lists__name", flat=True)

    def test_selective_load(self):
        pack = testpack.create_testpack(models.TestList.objects.all(), self.tlcqs)
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        models.TestListCycle.objects.all().delete()

        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(
            fp,
            test_keys=[self.t1.natural_key()],
            test_list_keys=[self.tl1.natural_key()],
            cycle_keys=[],
        )

        assert models.TestList.objects.count() == 1
        assert models.Test.objects.count() == 1
        assert models.TestListCycle.objects.count() == 0

    def test_existing_created_user_not_overwritten(self):
        user2 = utils.create_user(uname="user2")
        pack = testpack.create_testpack(self.tlqs, self.tlcqs)

        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(fp, user2)

        assert models.TestList.objects.get(slug=self.tl1.slug).created_by != user2

    def test_existing_objs_not_deleted(self):
        pack = testpack.create_testpack(self.tlqs, self.tlcqs)

        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        testpack.load_testpack(
            fp,
            test_keys=[self.t1.natural_key()],
            test_list_keys=[self.tl1.natural_key()],
            cycle_keys=[],
        )

        assert models.TestList.objects.filter(name__in=[self.tl2.name, self.tl3.name]).count() == 2
        assert models.Test.objects.filter(name__in=[self.t2.name, self.t3.name]).count() == 2
        assert models.TestListCycle.objects.filter(name__in=[self.tlc.name]).count() == 1

    def test_extra_tests(self):
        extra = utils.create_test("extra test")
        extra_qs = models.Test.objects.filter(pk=extra.pk)
        pack = testpack.create_testpack(self.tlqs, self.tlcqs, extra_tests=extra_qs)
        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        assert "extra test" in fp.read()

    def test_extra_tests_loaded(self):
        extra = utils.create_test("extra test")
        extra_qs = models.Test.objects.filter(pk=extra.pk)
        pack = testpack.create_testpack(self.tlqs, self.tlcqs, extra_tests=extra_qs)
        fp = io.StringIO()
        testpack.save_testpack(pack, fp)
        fp.seek(0)
        models.Test.objects.all().delete()
        testpack.load_testpack(fp, test_keys=[extra.natural_key()], test_list_keys=[], cycle_keys=[])
        assert models.Test.objects.filter(name=extra.name).exists()

    def test_sublist(self):
        tl5 = utils.create_test_list("tl5")
        t5 = utils.create_test("t5")
        utils.create_test_list_membership(tl5, t5, order=0)
        utils.create_sublist(tl5, self.tl1, order=2)
        utils.create_sublist(tl5, self.tl2, order=3)
        pack = json.dumps(testpack.create_testpack(test_lists=models.TestList.objects.filter(pk=tl5.pk)))
        models.TestList.objects.all().delete()
        models.Test.objects.all().delete()
        assert models.Sublist.objects.count() == 0
        testpack.add_testpack(pack, test_list_keys=[tl5.natural_key()])
        assert models.Sublist.objects.count() == 2
        assert models.TestListMembership.objects.count() == 3
        for sl in models.Sublist.objects.all():
            assert sl.child.testlistmembership_set.count() == 1
        assert models.TestList.objects.count() == 3
        assert models.TestList.objects.get(name="tl5")


class TestCalcDueDate:

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
            name="MWF",
            slug="mwf",
            recurrences=recurrence.Recurrence(
                rrules=[rule],
                dtstart=timezone.datetime(2012, 1, 1, tzinfo=timezone.utc),
            ),
            window_end=7,
            window_start=7,
        )

    def test_adhoc(self):
        """Null frequency should result in a null due date"""
        assert qautils.calc_due_date(timezone.now(), timezone.now(), None) is None

    def test_daily_offset_due_today_before_due_time(self):
        """Daily frequency when performed today should result in due date one day in future"""
        daily = utils.create_frequency(name="d", slug="d", interval=1, save=False)
        six_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 6, 0))
        due = six_am_today + timezone.timedelta(hours=1)
        six_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 6, 0))
        assert qautils.calc_due_date(six_am_today, due, daily).date() == six_am_tmrw.date()

    def test_daily_offset_due_today_after_due_time(self):
        """Daily frequency when performed today should result in due date one day in future"""
        daily = utils.create_frequency(name="d", slug="d", interval=1, save=False)
        eight_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 8, 0))
        due = eight_am_today - timezone.timedelta(hours=1)
        eight_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 8, 0))
        assert qautils.calc_due_date(eight_am_today, due, daily).date() == eight_am_tmrw.date()

    def test_daily_offset_due_today_equal_due_time(self):
        """Daily frequency when performed today should result in due date one day in future"""
        daily = utils.create_frequency(name="d", slug="d", interval=1, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due = seven_am_today
        seven_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert qautils.calc_due_date(seven_am_today, due, daily).date() == seven_am_tmrw.date()

    def test_daily_offset_due_yesterday(self):
        """Daily frequency when performed today should result in due date one day in future"""
        daily = utils.create_frequency(name="d", slug="d", interval=1, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due = self.make_dt(timezone.datetime(2018, 11, 19, 7, 0))
        seven_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert qautils.calc_due_date(seven_am_today, due, daily).date() == seven_am_tmrw.date()

    def test_daily_offset_due_tomorrow(self):
        daily = utils.create_frequency(name="d", slug="d", interval=1, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        seven_am_tmrw = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert qautils.calc_due_date(seven_am_today, seven_am_tmrw, daily).date() == seven_am_tmrw.date()

    def test_monthly_offset(self):
        """Monthly frequency when performed today should result in due date 28 days in future"""
        monthly = utils.create_frequency(name="d", slug="d", interval=28, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due_date = timezone.now()  # arbitrary
        seven_am_4wks = self.make_dt(timezone.datetime(2018, 12, 18, 7, 0))
        assert qautils.calc_due_date(seven_am_today, due_date, monthly).date() == seven_am_4wks.date()

    def test_annual_offset(self):
        """Annual frequency when performed today should result in due date 300 days in future"""
        annual = utils.create_frequency(name="d", slug="d", interval=300, save=False)
        seven_am_today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 12, 20, 7, 0))  # arbitrary
        seven_am_300_days = self.make_dt(timezone.datetime(2019, 9, 16, 7, 0))
        assert qautils.calc_due_date(seven_am_today, due_date, annual).date() == seven_am_300_days.date()

    def test_mwf_perf_monday_before_due_time(self):
        """With a MWF test performed at 6am on a Monday, if the due date is 7 am, the due date should be set to Wed"""
        six_am_monday = self.make_dt(timezone.datetime(2018, 11, 19, 6, 0))
        seven_am_monday = self.make_dt(timezone.datetime(2018, 11, 19, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert qautils.calc_due_date(six_am_monday, seven_am_monday, self.mwf) == expected_due_date

    def test_mwf_perf_monday_after_due_time(self):
        """With a MWF test performed at 8am on a Monday, if the due date is 7 am, the due date should be set to Wed"""
        seven_am_monday = self.make_dt(timezone.datetime(2018, 11, 19, 7, 0))
        eight_am_monday = self.make_dt(timezone.datetime(2018, 11, 19, 8, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        assert qautils.calc_due_date(eight_am_monday, seven_am_monday, self.mwf) == expected_due_date

    def test_mwf_perf_tuesday(self):
        """With a MWF test performed on a Tuesday with a due date of Wed, the due date should be set to Wed"""
        seven_am_tues = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        seven_am_wed = self.make_dt(timezone.datetime(2018, 11, 21, 7, 0))
        expected_due_date = seven_am_wed
        assert qautils.calc_due_date(seven_am_tues, seven_am_wed, self.mwf) == expected_due_date

    def test_mwf_due_monday_perf_sat(self):
        """With a MWF test due Mon, performed on a Sat, the due date should be set to Mon"""
        seven_am_sat = self.make_dt(timezone.datetime(2018, 11, 24, 7, 0))
        seven_am_mon = self.make_dt(timezone.datetime(2018, 11, 26, 7, 0))
        expected_due_date = seven_am_mon
        assert qautils.calc_due_date(seven_am_sat, seven_am_mon, self.mwf) == expected_due_date

    def test_mwf_due_friday_perf_sat(self):
        """With a MWF test due Friday performed on a Sat, the due date should be set to Mon"""
        seven_am_fri = self.make_dt(timezone.datetime(2018, 11, 23, 7, 0))
        seven_am_sat = self.make_dt(timezone.datetime(2018, 11, 24, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 11, 26, 7, 0))
        assert qautils.calc_due_date(seven_am_sat, seven_am_fri, self.mwf) == expected_due_date

    def test_first_of_month_before_window(self):
        """With a first of month test performed in the middle of the month, the
        due date should unchanged"""
        today = self.make_dt(timezone.datetime(2018, 11, 20, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        expected_due_date = due_date
        assert qautils.calc_due_date(today, due_date, self.day_of_month(1)) == expected_due_date

    def test_first_of_month_in_window_before(self):
        """With a first of month test performed in the middle of the month, the
        due date should unchanged"""
        today = self.make_dt(timezone.datetime(2018, 11, 29, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        next_month = self.make_dt(timezone.datetime(2019, 1, 1, 7, 0))
        assert qautils.calc_due_date(today, due_date, self.day_of_month(1)) == next_month

    def test_first_of_month_performed_first_of_month(self):
        """With a first of month test performed on the first of the month, the
        due date should be set to first of next month"""
        today = self.make_dt(timezone.datetime(2018, 11, 1, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 11, 1, 7, 0))
        next_month = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        assert qautils.calc_due_date(today, due_date, self.day_of_month(1)).date() == next_month.date()

    def test_first_of_month_performed_after_first_of_month(self):
        """With a first of month test performed on the second of the month, the
        due date should be set to first of next month"""
        first_of_month = self.make_dt(timezone.datetime(2018, 11, 1, 7, 0))
        today = self.make_dt(timezone.datetime(2018, 11, 2, 7, 0))
        next_month = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        assert qautils.calc_due_date(today, first_of_month, self.day_of_month(1)).date() == next_month.date()

    def test_first_of_month_performed_day_before(self):
        """If a Test List is performed on e.g. the 31st, the due date should
        be advanced to the next month, not the next day"""
        today = self.make_dt(timezone.datetime(2018, 11, 30, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 12, 1, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2019, 1, 1, 7, 0))
        assert qautils.calc_due_date(today, due_date, self.day_of_month(1)).date() == expected_due_date.date()

    def test_wed_of_week_performed_mon(self):
        """If a Test List is due every Wed and performed on a Mon, the due date should be
        advanced 2 days forward, not the next day (obviously depends on config or frequency!)
        """
        mon = self.make_dt(timezone.datetime(2018, 11, 26, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 11, 28, 7, 0))
        assert qautils.calc_due_date(mon, due_date, self.wed).date() == due_date.date()

    def test_wed_of_week_performed_tues(self):
        """If a Test List is due every Wed and performed on a Tues, the due date should be
        advanced 8 days forward, not the next day
        """
        tue = self.make_dt(timezone.datetime(2018, 11, 27, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 11, 28, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 5, 7, 0))
        assert qautils.calc_due_date(tue, due_date, self.wed).date() == expected_due_date.date()

    def test_wed_of_week_performed_wed(self):
        """If a Test List is due every Wed and performed on a Wed, the due date should be
        advanced 7 days forward
        """
        wed = self.make_dt(timezone.datetime(2018, 11, 28, 7, 0))
        due_date = wed
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 5, 7, 0))
        assert qautils.calc_due_date(wed, due_date, self.wed).date() == expected_due_date.date()

    def test_wed_of_week_performed_thurs(self):
        """If a Test List is due every Wed and performed on a Wed, the due date should be
        advanced 7 days forward
        """
        thu = self.make_dt(timezone.datetime(2018, 11, 29, 7, 0))
        due_date = self.make_dt(timezone.datetime(2018, 11, 28, 7, 0))
        expected_due_date = self.make_dt(timezone.datetime(2018, 12, 5, 7, 0))
        assert qautils.calc_due_date(thu, due_date, self.wed).date() == expected_due_date.date()


class TestFormatQCValue:

    @override_settings(CONSTANT_PRECISION=2)
    def test_null_format(self):
        assert qautils.format_qc_value(1, None) == "1.0"

    @override_settings(CONSTANT_PRECISION=2)
    def test_empty_format(self):
        assert qautils.format_qc_value(1, "") == "1.0"

    def test_old_style(self):
        assert qautils.format_qc_value(1, "%.3f") == "1.000"

    def test_new_style(self):
        assert qautils.format_qc_value(1, "{:.3f}") == "1.000"

    @override_settings(CONSTANT_PRECISION=2)
    def test_invalid_format(self):
        assert qautils.format_qc_value(1, "{:foo}") == qautils.to_precision(1, settings.CONSTANT_PRECISION)

    def test_non_numerical_val(self):
        assert qautils.format_qc_value(None, "%d") == "None"

    @override_settings(DEFAULT_NUMBER_FORMAT="{:.3f}")
    def test_default_format_new(self):
        assert qautils.format_qc_value(1, "") == qautils.format_qc_value(1, "{:.3f}")

    @override_settings(DEFAULT_NUMBER_FORMAT="%.3f")
    def test_default_format_old(self):
        assert qautils.format_qc_value(1, None) == qautils.format_qc_value(1, "{:.3f}")

    @override_settings(DEFAULT_NUMBER_FORMAT="{:foo}")
    def test_invalid_default_fallback(self):
        assert qautils.format_qc_value(1, None) == qautils.to_precision(1, settings.CONSTANT_PRECISION)


class TestDateFunctions:

    def test_last_month_dates_jan(self):
        dt = timezone.datetime(2019, 1, 15, tzinfo=timezone.utc)
        start, end = qautils.last_month_dates(dt)
        tz = timezone.get_current_timezone()
        assert start == tz.localize(timezone.datetime(2018, 12, 1))
        assert end == tz.localize(timezone.datetime(2018, 12, 31))

    def test_last_month_dates_dec(self):
        dt = timezone.datetime(2019, 12, 15, tzinfo=timezone.utc)
        start, end = qautils.last_month_dates(dt)
        tz = timezone.get_current_timezone()
        assert start == tz.localize(timezone.datetime(2019, 11, 1))
        assert end == tz.localize(timezone.datetime(2019, 11, 30))
