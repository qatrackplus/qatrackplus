from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from django_comments.models import Comment

from qatrack.qa import models

from . import utils


def utc_2am():
    return timezone.make_aware(timezone.datetime(2014, 4, 2, 2), timezone.utc)


class TestFrequencyManager(TestCase):

    def test_choices(self):

        intervals = (
            ("Daily", "daily", 1, 1, 1),
            ("Weekly", "weekly", 7, 7, 9),
            ("Monthly", "monthly", 28, 28, 35),
        )
        for t, s, nom, due, overdue in intervals:
            utils.create_frequency(name=t, slug=s, nom=nom, due=due, overdue=overdue)
        self.assertEqual([(x[1], x[0]) for x in intervals], list(models.Frequency.objects.frequency_choices()))


class TestFrequency(TestCase):

    def test_nominal_delta(self):

        intervals = (
            ("Daily", "daily", 1, 1, 1),
            ("Weekly", "weekly", 7, 7, 9),
            ("Monthly", "monthly", 28, 28, 35),
        )
        for t, s, nom, due, overdue in intervals:
            f = utils.create_frequency(name=t, slug=s, nom=nom, due=due, overdue=overdue)
            expected_delta = timezone.timedelta(days=nom)
            self.assertEqual(expected_delta, f.nominal_delta())


class TestStatus(TestCase):

    def test_save_without_default(self):
        """If there's only one status type force it to be default on save"""
        self.assertIsNone(models.TestInstanceStatus.objects.default())
        status = models.TestInstanceStatus(name="foo", slug="foo", is_default=False, )
        status.save()
        self.assertEqual(status, models.TestInstanceStatus.objects.default())

    def test_new_default(self):
        status = models.TestInstanceStatus(name="foo", slug="foo", is_default=True, )
        status.save()

        new_status = models.TestInstanceStatus(name="bar", slug="bar", is_default=True, )
        new_status.save()

        defaults = models.TestInstanceStatus.objects.filter(is_default=True)
        self.assertEqual(list(defaults), [new_status])


class TestReference(TestCase):

    def test_invalid_value(self):
        u = utils.create_user()
        r = models.Reference(
            name="bool", type=models.BOOLEAN, value=3,
            created_by=u, modified_by=u
        )
        self.assertRaises(ValidationError, r.clean_fields)

    def test_display_value(self):
        t = models.Reference(type=models.BOOLEAN, value=1)
        f = models.Reference(type=models.BOOLEAN, value=0)
        v = models.Reference(type=models.NUMERICAL, value=0)
        n = models.Reference(type=models.NUMERICAL)

        self.assertTrue(t.value_display() == "Yes")
        self.assertTrue(f.value_display() == "No")
        self.assertTrue(v.value_display() == "0")
        self.assertTrue(n.value_display() == "")


class TestTolerance(TestCase):

    def test_pass_choices(self):
        t = models.Tolerance(mc_pass_choices="a,b,c")
        self.assertListEqual(["a", "b", "c"], t.pass_choices())

    def test_tol_choices(self):
        t = models.Tolerance(mc_tol_choices="a,b,c")
        self.assertListEqual(["a", "b", "c"], t.tol_choices())

    def test_no_pass_vals(self):
        t = models.Tolerance(mc_pass_choices=" ", type=models.MULTIPLE_CHOICE)
        self.assertRaises(ValidationError, t.clean_choices)

    def test_act_set(self):
        t = models.Tolerance(mc_pass_choices="", act_high=1, type=models.MULTIPLE_CHOICE)
        self.assertRaises(ValidationError, t.clean_choices)

    def test_pass_is_none(self):
        t = models.Tolerance(type=models.MULTIPLE_CHOICE)
        self.assertRaises(ValidationError, t.clean_choices)

    def test_with_tol_choices(self):
        t = models.Tolerance(mc_pass_choices="a", mc_tol_choices=" ", type=models.MULTIPLE_CHOICE)
        t.clean_choices()

    def test_ok_mc(self):
        t = models.Tolerance(mc_pass_choices="a", mc_tol_choices="b", type=models.MULTIPLE_CHOICE)
        t.clean_fields()
        self.assertListEqual(t.tol_choices(), ["b"])
        self.assertListEqual(t.pass_choices(), ["a"])

    def test_without_act(self):
        t = models.Tolerance(type=models.ABSOLUTE)
        self.assertRaises(ValidationError, t.clean_tols)

    def test_invalid_mc_choices(self):
        t = models.Tolerance(mc_pass_choices="a", type=models.ABSOLUTE)
        self.assertRaises(ValidationError, t.clean_choices)

        t = models.Tolerance(mc_tol_choices="a", type=models.ABSOLUTE)
        self.assertRaises(ValidationError, t.clean_choices)

    def test_no_pass_choices(self):
        t = models.Tolerance(mc_pass_choices="", type=models.MULTIPLE_CHOICE)
        self.assertRaises(ValidationError, t.clean_choices)

    def test_no_tol_choices(self):
        t = models.Tolerance(mc_pass_choices="a", mc_tol_choices="", type=models.MULTIPLE_CHOICE)
        t.clean_choices()
        t = models.Tolerance(mc_pass_choices="a", type=models.MULTIPLE_CHOICE)
        t.clean_choices()

    def test_tolerances_for_value_none(self):
        expected = {models.ACT_HIGH: None, models.ACT_LOW: None, models.TOL_LOW: None, models.TOL_HIGH: None}
        t = models.Tolerance()
        self.assertDictEqual(t.tolerances_for_value(None), expected)

    def test_tolerances_for_value_absolute(self):
        expected = {models.ACT_HIGH: 55, models.ACT_LOW: 51, models.TOL_LOW: 52, models.TOL_HIGH: 54}
        t = models.Tolerance(act_high=2, act_low=-2, tol_high=1, tol_low=-1, type=models.ABSOLUTE)
        self.assertDictEqual(expected, t.tolerances_for_value(53))

    def test_tolerances_for_value_percent(self):
        expected = {models.ACT_HIGH: 1.02, models.ACT_LOW: 0.98, models.TOL_LOW: 0.99, models.TOL_HIGH: 1.01}
        t = models.Tolerance(act_high=2, act_low=-2, tol_high=1, tol_low=-1, type=models.PERCENT)
        self.assertDictEqual(expected, t.tolerances_for_value(1))

    def test_percent_string_rep(self):
        t = models.Tolerance(act_high=None, act_low=-2, tol_high=1, tol_low=None, type=models.PERCENT)
        self.assertEqual(t.name, "Percent(-2.00%, --, 1.00%, --)")

    def test_absolute_string_rep(self):
        t = models.Tolerance(act_high=None, act_low=-2, tol_high=1, tol_low=None, type=models.ABSOLUTE)
        self.assertEqual(t.name, "Absolute(-2.000, --, 1.000, --)")

    def test_mc_string_rep(self):
        t = models.Tolerance(mc_pass_choices="a,b,c", mc_tol_choices="d,e", type=models.MULTIPLE_CHOICE)
        self.assertEqual(t.name, "M.C.(%s=a:b:c, %s=d:e)" % (settings.TEST_STATUS_DISPLAY['ok'], settings.TEST_STATUS_DISPLAY['tolerance']))


class TestCategory(TestCase):
    pass


class TestTestCollectionInterface(TestCase):

    def test_abstract_test_list_members(self):
        self.assertRaises(NotImplementedError, models.TestCollectionInterface().test_list_members)


class TestTest(TestCase):

    def test_is_boolean(self):
        test = utils.create_test(name="bool", test_type=models.BOOLEAN)
        self.assertTrue(test.is_boolean())

    def test_is_string(self):
        test = utils.create_test(name="bool", test_type=models.STRING)
        self.assertTrue(test.is_string())

    def test_is_string_composite(self):
        test = utils.create_test(name="bool", test_type=models.STRING_COMPOSITE)
        self.assertTrue(test.is_string_composite())

    def test_is_upload(self):
        test = utils.create_test(name="upload", test_type=models.UPLOAD)
        self.assertTrue(test.is_upload())

    def test_is_numerical_type(self):
        for t in (models.COMPOSITE, models.CONSTANT, models.SIMPLE):
            test = utils.create_test(name="num", test_type=t)
            self.assertTrue(test.is_numerical_type())

    def test_is_string_type(self):
        for t in (models.STRING_COMPOSITE, models.STRING, ):
            test = utils.create_test(name="num", test_type=t)
            self.assertTrue(test.is_string_type())

    def test_valid_check_test_type(self):
        test_types = (
            ("choices", "foo, bar", models.MULTIPLE_CHOICE, "Multiple Choice"),
            ("constant_value", 1.0, models.CONSTANT, "Constant"),
            ("calculation_procedure", "result=foo", models.COMPOSITE, "Composite"),
        )
        for attr, val, ttype, display in test_types:
            test = utils.create_test(name=display, test_type=ttype)
            setattr(test, attr, val)
            test.check_test_type(getattr(test, attr), ttype, display)

    def test_invalid_check_test_type(self):
        test_types = (
            ("choices", "foo, bar", models.CONSTANT, "Invalid"),
            ("constant_value", 1., models.COMPOSITE, "Constant"),
            ("calculation_procedure", "result=foo", models.MULTIPLE_CHOICE, "Composite"),
            ("choices", None, models.MULTIPLE_CHOICE, "Multiple Choice"),
            ("constant_value", None, models.COMPOSITE, "Constant"),
            ("calculation_procedure", None, models.COMPOSITE, "Composite"),

        )
        for attr, val, ttype, display in test_types:
            test = utils.create_test(name=display, test_type=ttype)
            setattr(test, attr, val)
            test_type = ttype if val is None else models.SIMPLE
            errors = test.check_test_type(getattr(test, attr), test_type, display)
            self.assertTrue(len(errors) > 0)

    def test_clean_calc_proc_not_needed(self):
        test = utils.create_test(test_type=models.SIMPLE)
        self.assertIsNone(test.clean_calculation_procedure())

    def test_invalid_clean_calculation_procedure(self):

        test = utils.create_test(test_type=models.COMPOSITE)

        invalid_calc_procedures = (
            "resul t = a + b",
            "_result = a + b",
            "0result = a+b",
            "result_=foo",
            "",
            "foo = a +b",
            "foo = __import__('bar')",
            "result = (a+b",
        )

        for icp in invalid_calc_procedures:
            test.calculation_procedure = icp
            try:
                msg = "Passed but should have failed:\n %s" % icp
                test.clean_calculation_procedure()
            except ValidationError:
                msg = ""
            self.assertTrue(len(msg) == 0, msg=msg)

    def test_valid_calc_procedure(self):

        test = utils.create_test(test_type=models.COMPOSITE)

        valid_calc_procedures = (
            "result = a + b",
            "result = 42",
            """foo = a + b
result = foo + bar""",
            """foo = a + b
result = foo + bar

    """
        )
        for vcp in valid_calc_procedures:
            test.calculation_procedure = vcp
            try:
                msg = ""
                test.clean_calculation_procedure()
            except ValidationError:
                msg = "Failed but should have passed:\n %s" % vcp
            self.assertTrue(len(msg) == 0, msg=msg)

    def test_clean_constant_value(self):
        test = utils.create_test(test_type=models.CONSTANT)
        self.assertRaises(ValidationError, test.clean_constant_value)
        test.constant_value = 1
        self.assertIsNone(test.clean_constant_value())

    def test_clean_mult_choice_not_needed(self):
        test = utils.create_test(test_type=models.SIMPLE)
        self.assertIsNone(test.clean_choices())

    def test_valid_mult_choice(self):
        test = utils.create_test(test_type=models.MULTIPLE_CHOICE)
        valid = ("foo, bar, baz", "foo, bar, baz", "foo, \tbar")
        for v in valid:
            test.choices = v
            test.clean_choices()

        test.choices = valid[0]
        test.clean_choices()
        self.assertListEqual([("foo", "foo"), ("bar", "bar"), ("baz", "baz")], test.get_choices())

    def test_invalid_mult_choice(self):
        test = utils.create_test(test_type=models.MULTIPLE_CHOICE)
        invalid = (None, "", " ", )
        for i in invalid:
            test.choices = i
            self.assertRaises(ValidationError, test.clean_choices)

    def test_invalid_clean_slug(self):
        test = utils.create_test()

        invalid = ("0 foo", "foo ", " foo" "foo bar", "foo*bar", "%foo", "foo$")

        for i in invalid:
            test.slug = i
            try:
                msg = "Short name should have failed but passed: %s" % i
                test.clean_slug()
            except ValidationError:
                msg = ""

            self.assertTrue(len(msg) == 0, msg=msg)
        test.type = models.COMPOSITE
        test.slug = ""

        self.assertRaises(ValidationError, test.clean_slug)

    def test_valid_clean_slug(self):
        test = utils.create_test()
        valid = ("foo", "f6oo", "foo6", "_foo", "foo_", "foo_bar")
        for v in valid:
            test.slug = v
            try:
                msg = ""
                test.clean_slug()
            except ValidationError:
                msg = "Short name should have passed but failed: %s" % v
            self.assertTrue(len(msg) == 0, msg=msg)

    def test_clean_fields(self):
        test = utils.create_test()
        test.clean_fields()

    def test_get_choices(self):
        test = utils.create_test(test_type=models.MULTIPLE_CHOICE)
        test.choices = "a,b"

        self.assertEqual(test.get_choices(), [("a", "a"), ("b", "b")])


class TestOnTestSaveSignal(TestCase):

    def test_valid_bool_check(self):
        ref = utils.create_reference(value=3)
        uti = utils.create_unit_test_info(ref=ref)
        uti.test.type = models.BOOLEAN
        self.assertRaises(ValidationError, uti.test.save)


class TestUnitTestInfo(TestCase):

    def setUp(self):
        self.test = utils.create_test()
        self.test_list = utils.create_test_list()
        utils.create_test_list_membership(test=self.test, test_list=self.test_list)

        self.utc = utils.create_unit_test_collection(test_collection=self.test_list)
        self.uti = models.UnitTestInfo.objects.get(test=self.test, unit=self.utc.unit)
        self.tli = utils.create_test_list_instance(unit_test_collection=self.utc)

    def test_percentage_ref(self):
        self.uti.reference = utils.create_reference(value=0)
        self.uti.tolerance = utils.create_tolerance(tol_type=models.PERCENT)
        self.assertRaises(ValidationError, self.uti.clean)

    def test_boolean_ref(self):

        self.uti.reference = utils.create_reference(value=3)
        self.uti.test.type = models.BOOLEAN
        self.assertRaises(ValidationError, self.uti.clean)

    def test_history(self):
        td = timezone.timedelta
        now = timezone.now()

        status = utils.create_status()

        # values purposely utils.created out of order to make sure history
        # returns in correct order (i.e. ordered by date)
        history = [
            (now + td(days=4), 5., models.NO_TOL, status),
            (now + td(days=1), 5., models.NO_TOL, status),
            (now + td(days=3), 6., models.NO_TOL, status),
            (now + td(days=2), 7., models.NO_TOL, status),
        ]

        for wc, val, _, _ in history:
            utils.create_test_instance(self.tli, unit_test_info=self.uti, status=status, work_completed=wc, value=val)

        sorted_hist = list(sorted([(x[0].replace(second=0, microsecond=0), x[1], x[2], x[3]) for x in history]))
        uti_hist = [(x[0].replace(second=0, microsecond=0), x[1], x[2], x[3]) for x in self.uti.get_history()]
        self.assertListEqual(sorted_hist, uti_hist)

        # test returns correct number of results
        limited = [(x[0].replace(second=0, microsecond=0), x[1], x[2], x[3]) for x in self.uti.get_history(number=2)]
        self.assertListEqual(sorted_hist[-2:], limited)

    def test_add_to_cycle(self):
        models.UnitTestInfo.objects.all().delete()
        tl1 = utils.create_test_list("tl1")
        tl2 = utils.create_test_list("tl2")
        t1 = utils.create_test("t1")
        t2 = utils.create_test("t2")
        utils.create_test_list_membership(tl1, t1)
        utils.create_test_list_membership(tl2, t2)

        cycle = utils.create_cycle(test_lists=[tl1, tl2])

        utils.create_unit_test_collection(test_collection=cycle, unit=self.utc.unit, frequency=self.utc.frequency)

        utis = models.UnitTestInfo.objects.all()

        self.assertEqual(len(utis), 2)
        t3 = utils.create_test("t3")
        utils.create_test_list_membership(tl2, t3)

        utis = models.UnitTestInfo.objects.all()
        self.assertEqual(len(utis), 3)

    def test_read_test(self):
        utis = models.UnitTestInfo.objects.all()
        self.assertEqual(utis.count(), 1)
        utis.delete()
        self.assertEqual(utis.count(), 0)
        self.test_list.save()
        self.assertEqual(models.UnitTestInfo.objects.count(), 1)

    def test_active_only_simple(self):

        utis = models.UnitTestInfo.objects.active()
        self.assertEqual(utis.count(), 1)
        self.utc.active = False
        self.utc.save()
        self.assertEqual(models.UnitTestInfo.objects.active().count(), 0)

    def test_active_only_with_multiple_lists(self):

        tl2 = utils.create_test_list("tl2")
        t2 = utils.create_test("t2")
        utils.create_test_list_membership(tl2, self.test)
        utils.create_test_list_membership(tl2, t2)
        utc2 = utils.create_unit_test_collection(test_collection=tl2, unit=self.utc.unit, frequency=self.utc.frequency)

        utis = models.UnitTestInfo.objects.active()
        # only 2 active because t1 and t2 shared between tl1 and tl2
        self.assertEqual(utis.count(), 2)

        # uti for t1 should stay active because it's present in utc2
        self.utc.active = False
        self.utc.save()

        self.assertEqual(models.UnitTestInfo.objects.active().count(), 2)

        utc2.active = False
        utc2.save()
        self.utc.active = True
        self.utc.save()
        self.assertEqual(models.UnitTestInfo.objects.active().count(), 1)

    def test_active_only_with_cycle(self):

        tl2 = utils.create_test_list("tl2")
        t2 = utils.create_test("t2")
        utils.create_test_list_membership(tl2, self.test)
        utils.create_test_list_membership(tl2, t2)
        utc2 = utils.create_unit_test_collection(unit=self.utc.unit, test_collection=tl2, frequency=self.utc.frequency)

        tl3 = utils.create_test_list("tl3")
        t3 = utils.create_test("t3")
        utils.create_test_list_membership(tl3, self.test)
        utils.create_test_list_membership(tl2, t3)
        tlc = utils.create_cycle([tl2, tl3])

        utc3 = utils.create_unit_test_collection(test_collection=tlc, unit=utc2.unit, frequency=utc2.frequency)

        utis = models.UnitTestInfo.objects.active()

        self.assertEqual(utis.count(), 3)

        # uti for t1 should stay active because it's present in utc2
        self.utc.active = False
        self.utc.save()

        # all still should be active since t1 is present in tl2
        self.assertEqual(models.UnitTestInfo.objects.active().count(), 3)

        utc2.active = False
        utc2.save()

        # all still should be active since tl2 is present in tlc
        self.assertEqual(models.UnitTestInfo.objects.active().count(), 3)

        self.utc.active = True
        self.utc.save()
        utc3.active = False
        utc3.save()

        # only utc1 is active now
        self.assertEqual(models.UnitTestInfo.objects.active().count(), 1)


class TestTestListMembership(TestCase):
    pass


class TestTestList(TestCase):

    def test_get_list(self):
        tl = models.TestList()
        self.assertEqual((0, tl), tl.get_list())

    def test_test_list_members(self):
        tl = utils.create_test_list()
        self.assertListEqual([tl], list(tl.test_list_members()))

    def test_get_next_list(self):
        tl = models.TestList()
        self.assertEqual((0, tl), tl.next_list(None))

    def test_first(self):
        tl = models.TestList()
        self.assertEqual(tl, tl.first())

    def test_all_tests(self):
        """"""
        tl = utils.create_test_list()
        tests = [utils.create_test(name="test %d" % i) for i in range(4)]
        for order, test in enumerate(tests):
            utils.create_test_list_membership(test_list=tl, test=test, order=order)

        self.assertSetEqual(set(tests), set(tl.all_tests()))

    def test_content_type(self):
        tl = utils.create_test_list()
        self.assertEqual(tl.content_type(), ContentType.objects.get(model="testlist"))

    def test_all_lists(self):
        tl1 = utils.create_test_list(name="1")
        tl2 = utils.create_test_list(name="2")
        models.Sublist.objects.create(parent=tl1, child=tl2)
        self.assertSetEqual(set([tl1, tl2]), set(tl1.all_lists()))

    def test_ordered_tests(self):
        tl1 = utils.create_test_list(name="1")
        tl2 = utils.create_test_list(name="2")
        t1 = utils.create_test()
        t2 = utils.create_test("test2")
        utils.create_test_list_membership(test_list=tl1, test=t1)
        utils.create_test_list_membership(test_list=tl2, test=t2)
        models.Sublist.objects.create(parent=tl1, child=tl2)

        self.assertListEqual(list(tl1.ordered_tests()), [t1, t2])

    def test_ordered_tests_sublist(self):
        tl1 = utils.create_test_list(name="1")
        tl2 = utils.create_test_list(name="2")
        tl3 = utils.create_test_list(name="3")
        t1a = utils.create_test()
        t1b = utils.create_test()
        t2a = utils.create_test("test2a")
        t2b = utils.create_test("test2b")
        t3 = utils.create_test("test3")

        utils.create_test_list_membership(test_list=tl1, test=t1a, order=0)  # 0
        utils.create_test_list_membership(test_list=tl1, test=t1b, order=4)  # 4

        utils.create_test_list_membership(test_list=tl2, test=t2a, order=1)  # 2
        utils.create_test_list_membership(test_list=tl2, test=t2b, order=0)  # 1

        utils.create_test_list_membership(test_list=tl3, test=t3, order=0)  # 3

        models.Sublist.objects.create(parent=tl1, child=tl2, order=1)
        models.Sublist.objects.create(parent=tl1, child=tl3, order=3)

        self.assertListEqual(list(tl1.ordered_tests()), [t1a, t2b, t2a, t3, t1b])

    def test_len(self):
        self.assertEqual(1, len(utils.create_test_list()))


class TestTestListCycle(TestCase):

    def setUp(self):
        super(TestTestListCycle, self).setUp()

        daily = utils.create_frequency(nom=1, due=1, overdue=1)
        utils.create_status()

        self.empty_cycle = utils.create_cycle(name="empty")
        utc = utils.create_unit_test_collection(test_collection=self.empty_cycle, frequency=daily)

        self.test_lists = [utils.create_test_list(name="test list %d" % i) for i in range(2)]
        self.tests = []
        for i, test_list in enumerate(self.test_lists):
            test = utils.create_test(name="test %d" % i)
            utils.create_test_list_membership(test_list, test)
            self.tests.append(test)
        self.cycle = utils.create_cycle(test_lists=self.test_lists)

        utc = utils.create_unit_test_collection(test_collection=self.cycle, frequency=daily, unit=utc.unit)

    def test_get_list(self):
        for day, test_list in enumerate(self.test_lists):
            self.assertEqual((day, test_list), self.cycle.get_list(day))

        self.assertEqual((None, None), self.empty_cycle.get_list())

    def test_cycle_test_list_members(self):
        self.assertListEqual(self.test_lists, list(self.cycle.test_list_members()))

    def test_get_next_list(self):
        next_ = self.cycle.next_list(0)
        self.assertEqual((1, self.test_lists[1]), next_)

        next_ = self.cycle.next_list(1)
        self.assertEqual((0, self.cycle.first()), next_)

        self.assertEqual((None, None), self.empty_cycle.next_list(None))

    def test_first(self):
        self.assertEqual(self.cycle.first(), self.test_lists[0])
        self.assertFalse(self.empty_cycle.first())

    def test_all_tests(self):
        self.assertSetEqual(set(self.tests), set(self.cycle.all_tests()))
        self.assertEqual(0, self.empty_cycle.all_tests().count())

    def test_content_type(self):
        tl = utils.create_test_list()
        self.assertEqual(tl.content_type(), ContentType.objects.get(model="testlist"))

    def test_all_lists(self):
        self.assertSetEqual(set(self.test_lists), set(self.cycle.all_lists()))
        self.assertFalse(self.empty_cycle.all_lists())

    def test_len(self):
        self.assertEqual(0, len(models.TestListCycle()))
        self.assertEqual(2, len(self.cycle))
        self.assertEqual(0, len(self.empty_cycle))


class TestUTCDueDates(TestCase):

    def setUp(self):
        test = utils.create_test()
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test=test, test_list=test_list)

        self.valid_status = models.TestInstanceStatus(name="valid", slug="valid", is_default=True, requires_review=True, valid=True)
        self.valid_status.save()

        self.invalid_status = models.TestInstanceStatus(name="invalid", slug="invalid", is_default=False, requires_review=False, valid=False)
        self.invalid_status.save()

        self.daily = utils.create_frequency(name="daily", slug="daily", nom=1, due=1, overdue=1)
        self.monthly = utils.create_frequency(name="monthly", slug="monthly", nom=28, due=28, overdue=35)
        self.utc_hist = utils.create_unit_test_collection(test_collection=test_list, frequency=self.daily)
        self.uti_hist = models.UnitTestInfo.objects.get(test=test, unit=self.utc_hist.unit)

    def test_no_history(self):
        self.assertIsNone(self.utc_hist.due_date)

    def test_basic(self):
        # test case where utc is completed with valid status
        now = timezone.now()
        tli = utils.create_test_list_instance(unit_test_collection=self.utc_hist, work_completed=now)
        utils.create_test_instance(tli, unit_test_info=self.uti_hist, status=self.valid_status)
        self.utc_hist = models.UnitTestCollection.objects.get(pk=self.utc_hist.pk)
        self.assertEqual(self.utc_hist.due_date.date(), (now + self.utc_hist.frequency.due_delta()).date())

    def test_invalid_without_history(self):
        # test case where utc has no history and is completed with invalid status
        now = timezone.now()
        tli = utils.create_test_list_instance(unit_test_collection=self.utc_hist, work_completed=now)
        utils.create_test_instance(tli, unit_test_info=self.uti_hist, status=self.invalid_status)
        tli.save()

        self.utc_hist = models.UnitTestCollection.objects.get(pk=self.utc_hist.pk)
        self.assertEqual(self.utc_hist.due_date.date(), now.date())

    def test_modified_to_invalid(self):
        # test case where utc with history was created with valid status and
        # later changed to have invlaid status

        # first create valid history
        now = timezone.now()
        tli1 = utils.create_test_list_instance(unit_test_collection=self.utc_hist, work_completed=now)
        utils.create_test_instance(tli1, unit_test_info=self.uti_hist, status=self.valid_status)
        tli1.save()

        # now create 2nd valid history
        now = timezone.now()
        tli2 = utils.create_test_list_instance(unit_test_collection=self.utc_hist, work_completed=now + self.utc_hist.frequency.due_delta())
        ti2 = utils.create_test_instance(tli2, unit_test_info=self.uti_hist, status=self.valid_status)
        tli2.save()

        self.utc_hist = models.UnitTestCollection.objects.get(pk=self.utc_hist.pk)
        self.assertEqual(self.utc_hist.due_date.date(), (tli2.work_completed + self.utc_hist.frequency.due_delta()).date())

        # now mark ti2 as invali
        ti2.status = self.invalid_status
        ti2.save()

        self.utc_hist = models.UnitTestCollection.objects.get(pk=self.utc_hist.pk)
        self.utc_hist.set_due_date()

        self.assertEqual(self.utc_hist.due_date.date(), (tli1.work_completed + self.utc_hist.frequency.due_delta()).date())

    def test_modified_to_valid(self):
        # test case where test list was saved with invalid status and later
        # updated to have valid status

        # first create valid history
        now = timezone.now()
        tli1 = utils.create_test_list_instance(unit_test_collection=self.utc_hist, work_completed=now)
        utils.create_test_instance(tli1, unit_test_info=self.uti_hist, status=self.valid_status)
        tli1.save()

        # now create 2nd  with ivalid status
        now = timezone.now()
        tli2 = utils.create_test_list_instance(unit_test_collection=self.utc_hist, work_completed=now + self.utc_hist.frequency.due_delta())
        ti2 = utils.create_test_instance(tli2, unit_test_info=self.uti_hist, status=self.invalid_status)
        tli2.save()

        # due date should be based on tli1 since tli2 is invalid
        self.utc_hist = models.UnitTestCollection.objects.get(pk=self.utc_hist.pk)
        self.assertEqual(self.utc_hist.due_date.date(), (tli1.work_completed + self.utc_hist.frequency.due_delta()).date())

        # now mark ti2 as valid
        ti2.status = self.valid_status
        ti2.save()
        self.utc_hist.set_due_date()

        # due date should now be based on tli2 since it is valid
        self.assertEqual(self.utc_hist.due_date.date(), (tli2.work_completed + self.utc_hist.frequency.due_delta()).date())

    def test_due_date_not_updated_for_in_progress(self):
        # test case where utc with history was created with valid status and
        # later changed to have invlaid status

        # first create valid history
        now = timezone.now()
        tli1 = utils.create_test_list_instance(unit_test_collection=self.utc_hist, work_completed=now)
        utils.create_test_instance(tli1, unit_test_info=self.uti_hist, status=self.valid_status)
        tli1.save()

        # now create 2nd in progress history
        now = timezone.now()
        tli2 = utils.create_test_list_instance(unit_test_collection=self.utc_hist, work_completed=now + self.utc_hist.frequency.due_delta())
        utils.create_test_instance(tli2, unit_test_info=self.uti_hist, status=self.valid_status)
        tli2.in_progress = True
        tli2.save()

        self.utc_hist = models.UnitTestCollection.objects.get(pk=self.utc_hist.pk)
        self.assertEqual(self.utc_hist.due_date.date(), (tli1.work_completed + self.utc_hist.frequency.due_delta()).date())

    def test_cycle_due_date(self):
        test_lists = [utils.create_test_list(name="test list %d" % i) for i in range(2)]
        for i, test_list in enumerate(test_lists):
            test = utils.create_test(name="test %d" % i)
            utils.create_test_list_membership(test_list, test)
        cycle = utils.create_cycle(test_lists=test_lists)
        daily = utils.create_frequency(nom=1, due=1, overdue=1)
        status = utils.create_status()
        utc = utils.create_unit_test_collection(test_collection=cycle, frequency=daily, unit=self.utc_hist.unit)

        now = timezone.now()
        day, tl = utc.next_list()
        uti = models.UnitTestInfo.objects.get(test=tl.all_tests()[0], unit=utc.unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc, work_completed=now)
        utils.create_test_instance(tli, unit_test_info=uti, work_completed=now, status=status)

        tli.save()

        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertTrue(utils.datetimes_same(utc.due_date, now + daily.due_delta()))

        uti = models.UnitTestInfo.objects.get(test=test_lists[1].tests.all()[0], unit=utc.unit)

        utils.create_test_instance(tli, unit_test_info=uti, work_completed=now, status=status)
        self.assertTrue(utils.datetimes_same(timezone.localtime(utc.due_date), now + daily.due_delta()))


class TestUnitTestCollection(TestCase):

    def test_manager_by_unit(self):
        utc = utils.create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.by_unit(utc.unit)), [utc])

    def test_manager_by_frequency(self):
        utc = utils.create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.by_frequency(utc.frequency)), [utc])

    def test_manager_by_unit_frequency(self):
        utc = utils.create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.by_unit_frequency(utc.unit, utc.frequency)), [utc])

    def test_manager_test_lists(self):
        utc = utils.create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.test_lists()), [utc])

    def test_adhoc_due_status(self):
        now = timezone.now()

        utc = utils.create_unit_test_collection(frequency=None, null_frequency=True)

        self.assertEqual(models.NO_DUE_DATE, utc.due_status())
        utc.set_due_date(now - timezone.timedelta(days=1))

        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertEqual(utc.due_status(), models.OVERDUE)

    def test_daily_due_status(self):
        now = timezone.now()

        daily = utils.create_frequency(nom=1, due=1, overdue=1)

        utc = utils.create_unit_test_collection(frequency=daily)

        self.assertEqual(models.NO_DUE_DATE, utc.due_status())

        daily_statuses = (
            (-2, models.OVERDUE),
            (-1, models.OVERDUE),
            (0, models.NOT_DUE),
            (1, models.NOT_DUE)
        )
        for delta, due_status in daily_statuses:
            wc = now + timezone.timedelta(days=delta)
            utils.create_test_list_instance(unit_test_collection=utc, work_completed=wc)

            utc = models.UnitTestCollection.objects.get(pk=utc.pk)
            self.assertEqual(utc.due_status(), due_status)

    def test_weekly_due_status(self):
        now = timezone.now()

        weekly = utils.create_frequency(nom=7, due=7, overdue=9)
        utc = utils.create_unit_test_collection(frequency=weekly)

        self.assertEqual(models.NO_DUE_DATE, utc.due_status())

        weekly_statuses = (
            (-10, models.OVERDUE),
            (-8, models.DUE),
            (-7, models.DUE),
            (-6, models.NOT_DUE),
            (1, models.NOT_DUE)
        )
        for delta, due_status in weekly_statuses:
            wc = now + timezone.timedelta(days=delta)
            utils.create_test_list_instance(unit_test_collection=utc, work_completed=wc)
            utc = models.UnitTestCollection.objects.get(pk=utc.pk)
            self.assertEqual(utc.due_status(), due_status)

    @mock.patch('django.utils.timezone.now', mock.Mock(side_effect=utc_2am))
    def test_date_straddle_due_status(self):
        """
        Ensure that due_status is correct when test list is due tomorrow
        and current local time + UTC offset crosses midnight.
        e.g. the situation where:
            utc.due_date ==  2 April 2014 14:00 (UTC)
            timezone.localtime(timezone.now()).date() == 1 April 2014
            but
            timezone.now().date() == 2 April 2014
        """

        with timezone.override("America/Toronto"):
            weekly = utils.create_frequency(nom=7, due=7, overdue=9)
            utc = utils.create_unit_test_collection(frequency=weekly)
            utc.set_due_date(utc_2am() + timezone.timedelta(hours=12))
            utc = models.UnitTestCollection.objects.get(pk=utc.pk)
            self.assertEqual(utc.due_status(), models.NOT_DUE)

    def test_set_due_date(self):

        due_date = timezone.now() + timezone.timedelta(days=1)
        utc = utils.create_unit_test_collection()
        utc.set_due_date(due_date)
        self.assertEqual(utc.due_date, due_date)

    def test_set_due_date_none(self):
        now = timezone.now()
        utc = utils.create_unit_test_collection()
        utils.create_test_list_instance(unit_test_collection=utc, work_completed=now)
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        utc.set_due_date()
        due = now + timezone.timedelta(utc.frequency.due_interval)

        self.assertTrue(utils.datetimes_same(utc.due_date, due))

    def test_last_done_date(self):
        now = timezone.now()
        utc = utils.create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())
        tli = utils.create_test_list_instance(unit_test_collection=utc, work_completed=now)
        test = utils.create_test(name="tester")
        utils.create_test_list_membership(tli.test_list, test)

        uti = models.UnitTestInfo.objects.get(test=test, unit=utc.unit)

        utils.create_test_instance(tli, unit_test_info=uti, work_completed=now)
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertTrue(utils.datetimes_same(now, utc.last_done_date()))

    def test_unreviewed_instances(self):
        utc = utils.create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        test = utils.create_test(name="tester")
        utils.create_test_list_membership(tli.test_list, test)
        # uti = utils.create_unit_test_info(test=test, unit=utc.unit, frequency=utc.frequency)
        uti = models.UnitTestInfo.objects.get(test=test, unit=utc.unit)
        utils.create_test_instance(tli, unit_test_info=uti)
        self.assertEqual([tli], list(utc.unreviewed_instances()))

    def test_last_completed_instance(self):
        utc = utils.create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())

        test = utils.create_test(name="tester")
        utils.create_test_list_membership(utc.tests_object, test)

        self.assertIsNone(utc.last_instance)

        uti = models.UnitTestInfo.objects.get(test=test, unit=utc.unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        utils.create_test_instance(tli, unit_test_info=uti)
        self.assertEqual(tli, utc.last_instance)

    def test_unreview_test_instances(self):
        utc = utils.create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())

        test = utils.create_test(name="tester")
        utils.create_test_list_membership(utc.tests_object, test)

        self.assertIsNone(utc.last_instance)

        tli = utils.create_test_list_instance(unit_test_collection=utc)
        uti = models.UnitTestInfo.objects.get(test=test, unit=utc.unit)
        ti = utils.create_test_instance(tli, unit_test_info=uti)
        self.assertEqual([ti], list(utc.unreviewed_test_instances()))

    def test_history(self):
        td = timezone.timedelta
        now = timezone.now()
        utc = utils.create_unit_test_collection()

        test = utils.create_test(name="tester")
        utils.create_test_list_membership(utc.tests_object, test)

        uti = models.UnitTestInfo.objects.latest("pk")
        status = utils.create_status()

        # values purposely utils.created out of order to make sure history
        # returns in correct order (i.e. ordered by date)
        history = [
            now - td(days=4), now - td(days=1), now - td(days=3), now - td(days=2),
        ]

        tlis = []
        tis = []
        for wc in history:
            tli = utils.create_test_list_instance(unit_test_collection=utc, work_completed=wc)
            ti = utils.create_test_instance(tli, unit_test_info=uti, work_completed=wc, status=status)
            tis.append(ti)
            tlis.append(tli)

        tlis.sort(key=lambda x: x.work_completed, reverse=True)
        tis.sort(key=lambda x: x.work_completed, reverse=True)

        sorted_hist = list(reversed(sorted([h.replace(second=0, microsecond=0) for h in history])))

        test_hist, dates = utc.history(before=now)

        dates = [x.replace(second=0, microsecond=0) for x in dates]
        wcs = [x.work_completed.replace(second=0, microsecond=0) for x in tlis]

        self.assertEqual(sorted_hist, dates)
        self.assertEqual(sorted_hist, wcs)

        # test returns correct number of results
        self.assertEqual([(test, tis)], test_hist)

    def test_test_list_next_list(self):

        utc = utils.create_unit_test_collection()

        self.assertEqual(utc.next_list(), (0, utc.tests_object))

        utils.create_test_list_instance(unit_test_collection=utc)
        self.assertEqual(utc.next_list(), (0, utc.tests_object))

    def test_cycle_next_list_empty(self):

        cycle = utils.create_cycle()
        utc = utils.create_unit_test_collection(test_collection=cycle)

        self.assertEqual(utc.next_list(), (None, None))

    def test_cycle_next_list(self):

        test_lists = [utils.create_test_list(name="test list %d" % i) for i in range(2)]
        for i, test_list in enumerate(test_lists):
            test = utils.create_test(name="test %d" % i)
            utils.create_test_list_membership(test_list, test)

        cycle = utils.create_cycle(test_lists=test_lists)
        utc = utils.create_unit_test_collection(test_collection=cycle)

        self.assertEqual(utc.next_list(), (0, test_lists[0]))
        tli = utils.create_test_list_instance(unit_test_collection=utc, test_list=test_lists[0])

        # need to regrab from db since since last_instance was updated in the db
        # by signal handler
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertEqual(utc.next_list(), (1, test_lists[1]))

        work_completed = tli.work_completed + timezone.timedelta(hours=1)
        utils.create_test_list_instance(unit_test_collection=utc, test_list=test_lists[1], day=1, work_completed=work_completed)
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)

        self.assertEqual(utc.next_list(), (0, test_lists[0]))

    def test_cycle_next_list_with_repeats(self):

        test_lists = [utils.create_test_list(name="test list %d" % i) for i in range(2)]
        test_lists = test_lists + test_lists

        for i, test_list in enumerate(test_lists):
            test = utils.create_test(name="test %d" % i)
            utils.create_test_list_membership(test_list, test)

        cycle = utils.create_cycle(test_lists=test_lists)
        utc = utils.create_unit_test_collection(test_collection=cycle)

        self.assertEqual(utc.next_list(), (0, test_lists[0]))
        tli = utils.create_test_list_instance(unit_test_collection=utc, test_list=test_lists[0], day=2)

        # need to regrab from db since since last_instance was updated in the db
        # by signal handler
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertEqual(utc.next_list(), (3, test_lists[3]))
        work_completed = tli.work_completed + timezone.timedelta(hours=1)

        utils.create_test_list_instance(unit_test_collection=utc, test_list=test_lists[3], day=3, work_completed=work_completed)
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertEqual(utc.next_list(), (0, test_lists[0]))

    def test_cycle_get_list(self):

        test_lists = [utils.create_test_list(name="test list %d" % i) for i in range(2)]
        for i, test_list in enumerate(test_lists):
            test = utils.create_test(name="test %d" % i)
            utils.create_test_list_membership(test_list, test)

        cycle = utils.create_cycle(test_lists=test_lists)
        utc = utils.create_unit_test_collection(test_collection=cycle)

        for i, test_list in enumerate(test_lists):
            self.assertEqual(utc.get_list(i), (i, test_list))

        self.assertEqual(utc.get_list(), (0, test_lists[0]))

    def test_cycle_delete_day(self):

        test_lists = [utils.create_test_list(name="test list %d" % i) for i in range(2)]
        for i, test_list in enumerate(test_lists):
            test = utils.create_test(name="test %d" % i)
            utils.create_test_list_membership(test_list, test)

        cycle = utils.create_cycle(test_lists=test_lists)
        utc = utils.create_unit_test_collection(test_collection=cycle)

        self.assertEqual(utc.next_list(), (0, test_lists[0]))
        tli = utils.create_test_list_instance(unit_test_collection=utc, test_list=test_lists[0])

        membership = cycle.testlistcyclemembership_set.get(test_list=tli.test_list)
        membership.delete()
        cycle.testlistcyclemembership_set.filter(test_list=test_lists[1]).update(order=0)
        self.assertEqual(cycle.next_list(tli.day), (0, cycle.first()))

    def test_name(self):
        tl = utils.create_test_list("tl1")
        utc = utils.create_unit_test_collection(test_collection=tl)
        self.assertEqual(utc.name, str(utc))
        self.assertEqual(tl.name, utc.name)

    def test_delete_utc(self):

        utc = utils.create_unit_test_collection()

        tli = utils.create_test_list_instance(unit_test_collection=utc)
        tl = utc.tests_object
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertEqual(utc.last_instance, tli)
        utc.delete()

        self.assertRaises(
            models.UnitTestCollection.DoesNotExist,
            models.UnitTestCollection.objects.get, pk=utc.pk
        )

        self.assertRaises(
            models.TestListInstance.DoesNotExist,
            models.TestListInstance.objects.get, pk=tl.pk
        )


class TestSignals(TestCase):

    def test_list_assigned_to_unit(self):
        test = utils.create_test(name="test")
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test_list, test)

        utc = utils.create_unit_test_collection(test_collection=test_list)

        utis = list(models.UnitTestInfo.objects.all())

        # test list on its own
        self.assertEqual(len(utis), 1)
        self.assertListEqual([utc.unit, test], [utis[0].unit, utis[0].test])

        # test utis are utils.created for sublists
        sub_test = utils.create_test(name="sub")
        sub_list = utils.create_test_list(name="sublist")
        utils.create_test_list_membership(sub_list, sub_test)
        models.Sublist.objects.create(parent=test_list, child=sub_list)

        utis = list(models.UnitTestInfo.objects.all())
        self.assertEqual(len(utis), 2)
        self.assertListEqual([utc.unit, sub_test], [utis[1].unit, utis[1].test])

    def test_sublist_changed(self):
        test = utils.create_test(name="test")
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test_list, test)

        utc = utils.create_unit_test_collection(test_collection=test_list)

        # test utis are utils.created for sublists
        sub_test = utils.create_test(name="sub")
        sub_list = utils.create_test_list(name="sublist")
        utils.create_test_list_membership(sub_list, sub_test)
        models.Sublist.objects.create(parent=test_list, child=sub_list)

        utis = list(models.UnitTestInfo.objects.all())
        self.assertEqual(len(utis), 2)
        self.assertListEqual([utc.unit, sub_test], [utis[1].unit, utis[1].test])

        sub_test2 = utils.create_test(name="sub2")
        utils.create_test_list_membership(sub_list, sub_test2)
        utis = list(models.UnitTestInfo.objects.all())
        self.assertEqual(len(utis), 3)

    def test_test_cycle_changed(self):

        test_lists = [utils.create_test_list(name="test list %d" % i) for i in range(4)]
        tests = []
        for i, test_list in enumerate(test_lists):
            test = utils.create_test(name="test %d" % i)
            utils.create_test_list_membership(test_list, test)
            tests.append(test)

        cycle1 = utils.create_cycle(test_lists=test_lists[:2])
        cycle2 = utils.create_cycle(name="cycle2", test_lists=test_lists[2:])

        utc = utils.create_unit_test_collection(test_collection=cycle1)

        # change test collection
        utc.tests_object = cycle2
        utc.save()

        utis = list(models.UnitTestInfo.objects.all())

        # test list on its own
        self.assertEqual(len(utis), 4)
        self.assertListEqual(tests, [x.test for x in utis])


class TestTestInstance(TestCase):

    def setUp(self):
        self.test = utils.create_test()
        self.test_list = utils.create_test_list()
        utils.create_test_list_membership(test=self.test, test_list=self.test_list)
        self.utc = utils.create_unit_test_collection(test_collection=self.test_list)
        self.uti = models.UnitTestInfo.objects.get(test=self.test, unit=self.utc.unit)
        self.tli = utils.create_test_list_instance(unit_test_collection=self.utc)

    def test_save(self):
        ti = utils.create_test_instance(self.tli, unit_test_info=self.uti)
        ti.pass_fail = None
        self.assertIsNone(ti.pass_fail)
        ti.save()
        self.assertIsNotNone(ti.pass_fail)

    def test_diff(self):
        ref = utils.create_reference(value=1)
        ti = utils.create_test_instance(self.tli, unit_test_info=self.uti, value=1)
        ti.reference = ref
        self.assertEqual(0, ti.difference())

    def test_diff_unavailable(self):
        ti = utils.create_test_instance(self.tli, unit_test_info=self.uti, value=1)
        self.assertIsNone(ti.calculate_diff())

    def test_percent_diff(self):
        ref = utils.create_reference(value=1)
        ti = utils.create_test_instance(self.tli, unit_test_info=self.uti, value=1.1)
        ti.reference = ref
        self.assertAlmostEqual(10, ti.percent_difference())
        ref.value = 0
        self.assertRaises(ZeroDivisionError, ti.percent_difference)

    def test_bool_pass_fail(self):
        test = utils.create_test(test_type=models.BOOLEAN)
        uti = models.UnitTestInfo(test=test)

        yes_ref = models.Reference(type=models.BOOLEAN, value=True, )
        no_ref = models.Reference(type=models.BOOLEAN, value=False, )

        yes_instance = models.TestInstance(value=1, unit_test_info=uti)
        no_instance = models.TestInstance(value=0, unit_test_info=uti)

        ok_tests = (
            (yes_instance, yes_ref),
            (no_instance, no_ref),
        )
        action_tests = (
            (no_instance, yes_ref),
            (yes_instance, no_ref),
        )
        for i, ref in ok_tests:
            i.reference = ref
            i.calculate_pass_fail()
            self.assertEqual(models.OK, i.pass_fail)

        for i, ref in action_tests:
            i.reference = ref
            i.calculate_pass_fail()
            self.assertEqual(models.ACTION, i.pass_fail)

    def test_mult_pass_fail(self):
        test = models.Test(type=models.MULTIPLE_CHOICE, choices="a,b,c,d,e")

        t = models.Tolerance(type=models.MULTIPLE_CHOICE, mc_pass_choices="a,b", mc_tol_choices="c,d")
        uti = models.UnitTestInfo(test=test, tolerance=t)

        instance = models.TestInstance(test_list_instance=self.tli, unit_test_info=uti, tolerance=t)

        for c in ("a", "b"):
            instance.string_value = c
            instance.calculate_pass_fail()
            self.assertEqual(instance.pass_fail, models.OK)

        for c in ("c", "d"):
            instance.string_value = c
            instance.calculate_pass_fail()
            self.assertEqual(instance.pass_fail, models.TOLERANCE)

        for c in ("e", ):
            instance.string_value = c
            instance.calculate_pass_fail()
            self.assertEqual(instance.pass_fail, models.ACTION)

    def test_absolute_pass_fail(self):
        test = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=test)
        ti = models.TestInstance(unit_test_info=uti)
        ref = models.Reference(type=models.NUMERICAL, value=100.)
        ti.reference = ref
        tol = models.Tolerance(
            type=models.ABSOLUTE,
            act_low=-3,
            tol_low=-2,
            tol_high=2,
            act_high=3,
        )
        ti.tolerance = tol
        tests = (
            (models.ACTION, 96),
            (models.ACTION, -100),
            (models.ACTION, 1E99),
            (models.ACTION, 103.1),
            (models.TOLERANCE, 97),
            (models.TOLERANCE, 97.5),
            (models.TOLERANCE, 102.1),
            (models.TOLERANCE, 103),
            (models.OK, 100),
            (models.OK, 102),
            (models.OK, 98),
        )

        for result, val in tests:
            ti.value = val
            ti.calculate_pass_fail()
            self.assertEqual(result, ti.pass_fail)

    def test_absolute_no_action(self):
        test = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=test)
        ti = models.TestInstance(unit_test_info=uti)
        ref = models.Reference(type=models.NUMERICAL, value=100.)
        ti.reference = ref
        tol = models.Tolerance(
            type=models.ABSOLUTE,
            tol_low=-2,
            tol_high=2,
        )
        ti.tolerance = tol
        tests = (
            (models.TOLERANCE, 97),
            (models.TOLERANCE, 102.1),
            (models.OK, 100),
            (models.OK, 102),
            (models.OK, 98),
        )

        for result, val in tests:
            ti.value = val
            ti.calculate_pass_fail()
            self.assertEqual(result, ti.pass_fail)

    def test_edge_pass_fail(self):
        test = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=test)
        ti = models.TestInstance(unit_test_info=uti)
        ref = models.Reference(type=models.NUMERICAL, value=5.)
        ti.reference = ref
        tol = models.Tolerance(
            type=models.ABSOLUTE,
            act_low=-0.2,
            tol_low=-0.1,
            tol_high=0.1,
            act_high=0.2,
        )
        ti.tolerance = tol
        tests = (
            (models.ACTION, 4.79999),
            (models.TOLERANCE, 4.799999999999999999),
            (models.TOLERANCE, 4.8),

            (models.TOLERANCE, 4.89999),
            (models.OK, 4.899999999999999999),
            (models.OK, 4.9),


            (models.OK, 5.1),
            (models.OK, 5.10000000000000000000001),
            (models.TOLERANCE, 5.10001),

            (models.TOLERANCE, 5.2),
            (models.TOLERANCE, 5.20000000000000000000001),
            (models.ACTION, 5.20001),
        )

        for result, val in tests:
            ti.value = val
            ti.calculate_pass_fail()
            self.assertEqual(result, ti.pass_fail)

    def test_percent_pass_fail(self):
        test = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=test)
        ti = models.TestInstance(unit_test_info=uti)

        ti.reference = models.Reference(type=models.NUMERICAL, value=100.)
        ti.tolerance = models.Tolerance(
            type=models.PERCENT,
            act_low=-3,
            tol_low=-2,
            tol_high=2,
            act_high=3,
        )

        tests = (
            (models.ACTION, 96),
            (models.ACTION, -100),
            (models.ACTION, 1E99),
            (models.ACTION, 103.1),
            (models.TOLERANCE, 97),
            (models.TOLERANCE, 97.5),
            (models.TOLERANCE, 102.1),
            (models.TOLERANCE, 103),
            (models.OK, 100),
            (models.OK, 102),
            (models.OK, 98),
        )

        for result, val in tests:
            ti.value = val
            ti.calculate_pass_fail()
            self.assertEqual(result, ti.pass_fail)

    def test_skipped(self):
        ti = models.TestInstance(skipped=True)
        ti.unit_test_info = models.UnitTestInfo()
        ti.unit_test_info.test = models.Test(hidden=False)
        ti.calculate_pass_fail()
        self.assertEqual(models.NOT_DONE, ti.pass_fail)

    def test_in_progress(self):
        ti = utils.create_test_instance(self.tli, unit_test_info=self.uti)
        ti.test_list_instance.in_progress = True
        ti.test_list_instance.save()

        self.assertEqual(models.TestInstance.objects.in_progress()[0], ti)

    def test_upload_link_none(self):
        ti = utils.create_test_instance(self.tli, unit_test_info=self.uti)
        self.assertEqual(ti.upload_link(), None)

    def test_image_url_none(self):
        ti = utils.create_test_instance(self.tli, unit_test_info=self.uti)
        self.assertEqual(ti.image_url(), None)

    def test_upload_value_display(self):
        t = utils.create_test(test_type=models.UPLOAD)
        uti = utils.create_unit_test_info(test=t, unit=self.utc.unit, assigned_to=models.Group.objects.latest("id"))

        tli = utils.create_test_list_instance(unit_test_collection=self.utc)
        ti = utils.create_test_instance(tli, unit_test_info=uti)

        # no actual attachment so value display will be None
        self.assertEqual(None, ti.value_display())

    def test_string_value_display(self):
        t = models.Test(type=models.STRING)
        uti = models.UnitTestInfo(test=t)

        ti = models.TestInstance(unit_test_info=uti)
        ti.string_value = "test"

        self.assertEqual("test", ti.value_display())

    def test_bool_display_value(self):
        t = models.Test(type=models.BOOLEAN)
        uti = models.UnitTestInfo(test=t)

        ti = models.TestInstance(unit_test_info=uti, value=1)
        self.assertEqual("Yes", ti.value_display())

        ti = models.TestInstance(unit_test_info=uti, value=0)
        self.assertEqual("No", ti.value_display())

    def test_mc_display_value(self):
        t = models.Test(type=models.MULTIPLE_CHOICE, choices="a,b,c")
        uti = models.UnitTestInfo(test=t)

        ti = models.TestInstance(unit_test_info=uti, string_value="c")
        self.assertEqual("c", ti.value_display())

    def test_reg_display_value(self):
        t = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=t)

        ti = models.TestInstance(unit_test_info=uti, value=0)
        self.assertEqual("0", ti.value_display())

        ti.skipped = True
        self.assertEqual("Skipped", ti.value_display())

        ti.skipped = False
        ti.value = None
        self.assertEqual("Not Done", ti.value_display())

    def test_diff_display_no_value(self):
        t = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=t)

        ti = models.TestInstance(unit_test_info=uti, value=0)
        self.assertEqual("", ti.diff_display())

    def test_diff_display_absolute(self):
        t = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=t)

        tol = models.Tolerance(act_high=2, act_low=-2, tol_high=1, tol_low=-1, type=models.ABSOLUTE)
        ref = models.Reference(type=models.NUMERICAL, value=100.)

        ti = models.TestInstance(unit_test_info=uti, value=0, reference=ref, tolerance=tol)
        self.assertEqual("-100", ti.diff_display())

    def test_diff_display_percent(self):
        t = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=t)

        tol = models.Tolerance(act_high=2, act_low=-2, tol_high=1, tol_low=-1, type=models.PERCENT)
        ref = models.Reference(type=models.NUMERICAL, value=1.)

        ti = models.TestInstance(unit_test_info=uti, value=0.995, reference=ref, tolerance=tol)
        self.assertEqual("-0.5%", ti.diff_display())

    def test_diff_zero_div(self):
        t = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=t)

        tol = models.Tolerance(act_high=2, act_low=-2, tol_high=1, tol_low=-1, type=models.PERCENT)
        ref = models.Reference(type=models.NUMERICAL, value=0.)

        display = "Zero ref with % diff tol"
        ti = models.TestInstance(unit_test_info=uti, value=0.995, reference=ref, tolerance=tol)
        self.assertEqual(display, ti.diff_display())


class TestTestListInstance(TestCase):

    def setUp(self):
        self.tests = []

        self.ref = models.Reference(type=models.NUMERICAL, value=100.)
        self.tol = models.Tolerance(type=models.PERCENT, act_low=-3, tol_low=-2, tol_high=2, act_high=3)
        self.ref.created_by = utils.create_user()
        self.tol.created_by = utils.create_user()
        self.ref.modified_by = utils.create_user()
        self.tol.modified_by = utils.create_user()
        self.values = [None, None, 96, 97, 100, 100]

        self.statuses = [utils.create_status(name="status%d" % x, slug="status%d" % x) for x in range(len(self.values))]

        self.test_list = utils.create_test_list()
        for i in range(6):
            test = utils.create_test(name="name%d" % i)
            self.tests.append(test)
            utils.create_test_list_membership(self.test_list, test)

        self.unit_test_collection = utils.create_unit_test_collection(test_collection=self.test_list)

        self.test_list_instance = self.create_test_list_instance()

    def create_test_list_instance(self, work_completed=None):
        utc = self.unit_test_collection

        tli = utils.create_test_list_instance(unit_test_collection=utc, work_completed=work_completed)

        for i, (v, test, status) in enumerate(zip(self.values, self.tests, self.statuses)):
            uti = models.UnitTestInfo.objects.get(test=test, unit=utc.unit)
            ti = utils.create_test_instance(tli, unit_test_info=uti, value=v, status=status)
            ti.reference = self.ref
            ti.tolerance = self.tol
            ti.test_list_instance = tli
            if i == 0:
                ti.skipped = True
            if i == 1:
                ti.tolerance = None
                ti.reference = None
            else:
                ti.reference.save()
                ti.tolerance.save()
            ti.save()
        tli.save()
        return tli

    def test_pass_fail(self):

        pf_status = self.test_list_instance.pass_fail_status()
        for pass_fail, _, tests in pf_status:
            if pass_fail == models.OK:
                self.assertTrue(len(tests) == 2)
            else:
                self.assertTrue(len(tests) == 1)

    def test_review_status(self):

        for stat, tests in self.test_list_instance.status():
            self.assertEqual(len(tests), 1)

    def test_unreviewed_instances(self):

        self.assertSetEqual(
            set(self.test_list_instance.unreviewed_instances()),
            set(models.TestInstance.objects.all())
        )

    def test_tolerance_tests(self):
        self.assertEqual(1, self.test_list_instance.tolerance_tests().count())

    def test_failing_tests(self):
        self.assertEqual(1, self.test_list_instance.tolerance_tests().count())

    def test_in_progress(self):
        self.test_list_instance.in_progress = True
        self.test_list_instance.save()
        self.assertEqual(
            models.TestListInstance.objects.in_progress()[0],
            self.test_list_instance
        )

    def test_deleted_signal_tis_deleted(self):
        self.test_list_instance.delete()
        self.assertEqual(models.TestInstance.objects.count(), 0)

    def test_deleted_signal_last_instance_updated(self):

        tli = self.create_test_list_instance()
        self.unit_test_collection = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(self.unit_test_collection.last_instance, tli)

        tli.delete()
        self.unit_test_collection = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(self.unit_test_collection.last_instance, self.test_list_instance)

        self.test_list_instance.delete()
        self.unit_test_collection = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(self.unit_test_collection.last_instance, None)

    def test_input_later(self):
        dt = timezone.now() + timezone.timedelta(seconds=1)
        tli = self.create_test_list_instance(work_completed=dt)
        utc = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(utc.last_instance, tli)

        tli.work_completed = dt - timezone.timedelta(days=1)
        tli.save()

        utc = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(utc.last_instance, self.test_list_instance)


class TestAutoReview(TestCase):

    def setUp(self):
        self.tests = []

        self.ref = models.Reference(type=models.NUMERICAL, value=100.)
        self.tol = models.Tolerance(type=models.PERCENT, act_low=-3, tol_low=-2, tol_high=2, act_high=3)
        self.ref.created_by = utils.create_user()
        self.tol.created_by = utils.create_user()
        self.ref.modified_by = utils.create_user()
        self.tol.modified_by = utils.create_user()
        self.values = [96, 97, 100]

        self.statuses = [
            utils.create_status(name="default", slug="default", requires_review=True, is_default=True),
            utils.create_status(name="pass", slug="pass", requires_review=False, is_default=False),
            utils.create_status(name="tol", slug="tol", requires_review=False, is_default=False),
            utils.create_status(name="fail", slug="fail", requires_review=False, is_default=False),
        ]

        models.AutoReviewRule.objects.bulk_create([
            models.AutoReviewRule(pass_fail=models.OK, status=self.statuses[1]),
            models.AutoReviewRule(pass_fail=models.TOLERANCE, status=self.statuses[2]),
        ])

        self.test_list = utils.create_test_list()
        for i in range(3):
            test = utils.create_test(name="name%d" % i)
            test.auto_review = True
            test.save()

            self.tests.append(test)
            utils.create_test_list_membership(self.test_list, test)

        self.unit_test_collection = utils.create_unit_test_collection(test_collection=self.test_list)

        self.test_list_instance = self.create_test_list_instance()

    def create_test_list_instance(self):
        utc = self.unit_test_collection

        tli = utils.create_test_list_instance(unit_test_collection=utc)

        self.ref.save()
        self.tol.save()

        for i, (v, test) in enumerate(zip(self.values, self.tests)):
            uti = models.UnitTestInfo.objects.get(test=test, unit=utc.unit)
            ti = utils.create_test_instance(tli, unit_test_info=uti, value=v, status=self.statuses[0])
            ti.reference = self.ref
            ti.tolerance = self.tol
            ti.test_list_instance = tli
            ti.calculate_pass_fail()
            ti.auto_review()
            ti.save()

        tli.save()
        return tli

    def test_review_status(self):
        """Each of the three tests should have a different status"""

        for stat, tests in self.test_list_instance.status():
            self.assertEqual(len(tests), 1)

    def test_review_status_with_comment(self):
        """Each of the three tests should have a different status"""

        uti = models.UnitTestInfo.objects.get(test=self.tests[0], unit=self.unit_test_collection.unit)
        ti = utils.create_test_instance(self.test_list_instance, unit_test_info=uti, value=self.ref.value, status=self.statuses[0])
        ti.reference = self.ref
        ti.tolerance = self.tol
        ti.comment = "comment"
        ti.calculate_pass_fail()
        ti.auto_review()
        ti.save()
        self.assertTrue(ti.status.requires_review)

    def test_review_status_with_tli_comment(self):
        """Each of the three tests should have a different status"""

        uti = models.UnitTestInfo.objects.get(test=self.tests[0], unit=self.unit_test_collection.unit)
        ti = utils.create_test_instance(self.test_list_instance, unit_test_info=uti, value=self.ref.value, status=self.statuses[0])
        ti.reference = self.ref
        ti.tolerance = self.tol
        c = Comment.objects.create(comment="comment", content_type_id=999, site_id=1)
        self.test_list_instance.comments.add(c)
        # self.test_list_instance.save()
        ti.calculate_pass_fail()
        ti.auto_review()
        ti.save()
        self.assertTrue(ti.status.requires_review)

    def test_review_status_skipped_hidden(self):
        """Skipped hidden tests should not block auto review"""

        uti = models.UnitTestInfo.objects.get(test=self.tests[0], unit=self.unit_test_collection.unit)
        uti.test.hidden = True
        uti.test.save()
        ti = utils.create_test_instance(self.test_list_instance, unit_test_info=uti, value=self.ref.value, status=self.statuses[0])
        ti.skipped = True
        ti.reference = self.ref
        ti.tolerance = self.tol
        ti.calculate_pass_fail()
        ti.auto_review()
        ti.save()
        assert not ti.status.requires_review
