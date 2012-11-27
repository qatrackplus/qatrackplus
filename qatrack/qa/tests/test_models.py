from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import Client
from django.test.utils import setup_test_environment
from django.utils import unittest,timezone

from django.contrib.auth.models import User, Group
from qatrack.qa import models
from qatrack.qa import *
from qatrack.units.models import Unit, UnitType, Modality, ELECTRON, PHOTON

import re

import utils

#============================================================================
class TestFrequencyManager(TestCase):
    #----------------------------------------------------------------------
    def test_choices(self):

        intervals = (
            ("Daily","daily",1,1,1),
            ("Weekly","weekly",7,7,9),
            ("Monthly","monthly",28,28,35),
        )
        for t,s,nom,due,overdue in intervals:
            utils.create_frequency(name=t,slug=s,nom=nom,due=due,overdue=overdue)
        self.assertEqual([(x[1],x[0]) for x in intervals], list(models.Frequency.objects.frequency_choices()))

#============================================================================
class TestFrequency(TestCase):
    #----------------------------------------------------------------------
    def test_nominal_delta(self):

        intervals = (
            ("Daily","daily",1,1,1),
            ("Weekly","weekly",7,7,9),
            ("Monthly","monthly",28,28,35),
        )
        for t,s,nom,due,overdue in intervals:
            f = utils.create_frequency(name=t,slug=s,nom=nom,due=due,overdue=overdue)
            expected_delta = timezone.timedelta(days=nom)
            self.assertEqual(expected_delta,f.nominal_delta())

class TestStatus(TestCase):
    #----------------------------------------------------------------------
    def test_save_without_default(self):
        """If there's only one status type force it to be default on save"""
        self.assertIsNone(models.TestInstanceStatus.objects.default())
        status = models.TestInstanceStatus(name="foo",slug="foo",is_default=False,)
        status.save()
        self.assertEqual(status,models.TestInstanceStatus.objects.default())
    #----------------------------------------------------------------------
    def test_new_default(self):
        status = models.TestInstanceStatus(name="foo",slug="foo",is_default=True,)
        status.save()

        new_status = models.TestInstanceStatus(name="bar",slug="bar",is_default=True,)
        new_status.save()

        defaults = models.TestInstanceStatus.objects.filter(is_default=True)
        self.assertEqual(list(defaults),[new_status])

#============================================================================
class TestReference(TestCase):

    #----------------------------------------------------------------------
    def test_invalid_value(self):
        u = utils.create_user()
        r = models.Reference(
            name="bool",type=models.BOOLEAN,value=3,
            created_by=u, modified_by=u
        )
        self.assertRaises(ValidationError,r.clean_fields)
    #----------------------------------------------------------------------
    def test_display_value(self):
        t = models.Reference(type=models.BOOLEAN,value=1        )
        f = models.Reference(type=models.BOOLEAN,value=0        )
        v = models.Reference(type=models.NUMERICAL,value=0        )
        n = models.Reference(type=models.NUMERICAL)

        self.assertTrue(t.value_display() == "Yes")
        self.assertTrue(f.value_display() == "No")
        self.assertTrue(v.value_display() == "0")
        self.assertTrue(n.value_display() == "")

#====================================================================================
class TestTolerance(TestCase):
    #----------------------------------------------------------------------
    def test_pass_choices(self):
        t = models.Tolerance(mc_pass_choices="a,b,c")
        self.assertListEqual(["a","b","c"],t.pass_choices())
    #----------------------------------------------------------------------
    def test_tol_choices(self):
        t = models.Tolerance(mc_tol_choices="a,b,c")
        self.assertListEqual(["a","b","c"],t.tol_choices())

    #----------------------------------------------------------------------
    def test_no_pass_vals(self):
        t = models.Tolerance(mc_pass_choices=" ",type=models.MULTIPLE_CHOICE)
        self.assertRaises(ValidationError,t.clean_choices)
    #----------------------------------------------------------------------
    def test_act_set(self):
        t = models.Tolerance(mc_pass_choices="",act_high=1,type=models.MULTIPLE_CHOICE)
        self.assertRaises(ValidationError,t.clean_choices)
    #----------------------------------------------------------------------
    def test_pass_is_none(self):
        t = models.Tolerance(type=models.MULTIPLE_CHOICE)
        self.assertRaises(ValidationError,t.clean_choices)
    #----------------------------------------------------------------------
    def test_with_tol_choices(self):
        t = models.Tolerance(mc_pass_choices="a",mc_tol_choices=" ",type=models.MULTIPLE_CHOICE)
        t.clean_choices()

    #----------------------------------------------------------------------
    def test_ok_mc(self):
        t = models.Tolerance(name="foo",mc_pass_choices="a",mc_tol_choices="b",type=models.MULTIPLE_CHOICE)
        t.clean_fields()
        self.assertListEqual(t.tol_choices(),["b"])
        self.assertListEqual(t.pass_choices(),["a"])
    #----------------------------------------------------------------------
    def test_mc_repr(self):

        t = models.Tolerance(name="foo",type=models.MULTIPLE_CHOICE)
        self.assertIsInstance(t.__unicode__(),basestring)

    #----------------------------------------------------------------------
    def test_without_act(self):
        t = models.Tolerance(name="foo",type=models.ABSOLUTE)
        self.assertRaises(ValidationError,t.clean_tols)
    #----------------------------------------------------------------------
    def test_invalid_mc_choices(self):
        t = models.Tolerance(name="foo",mc_pass_choices="a",type=models.ABSOLUTE)
        self.assertRaises(ValidationError,t.clean_choices)

        t = models.Tolerance(name="foo",mc_tol_choices="a",type=models.ABSOLUTE)
        self.assertRaises(ValidationError,t.clean_choices)
    #----------------------------------------------------------------------
    def test_no_pass_choices(self):
        t = models.Tolerance(name="foo",mc_pass_choices="",type=models.MULTIPLE_CHOICE)
        self.assertRaises(ValidationError,t.clean_choices)

    #----------------------------------------------------------------------
    def test_no_tol_choices(self):
        t = models.Tolerance(name="foo",mc_pass_choices="a",mc_tol_choices="",type=models.MULTIPLE_CHOICE)
        t.clean_choices()
        t = models.Tolerance(name="foo",mc_pass_choices="a",type=models.MULTIPLE_CHOICE)
        t.clean_choices()
    #----------------------------------------------------------------------
    def test_tolerances_for_value_none(self):
        expected = {models.ACT_HIGH:None,models.ACT_LOW:None,models.TOL_LOW:None,models.TOL_HIGH:None}
        t = models.Tolerance()
        self.assertDictEqual(t.tolerances_for_value(None),expected)
    #----------------------------------------------------------------------
    def test_tolerances_for_value_absolute(self):
        expected = {models.ACT_HIGH:55,models.ACT_LOW:51,models.TOL_LOW:52,models.TOL_HIGH:54}
        t = models.Tolerance(act_high=2,act_low=-2,tol_high=1,tol_low=-1,type=models.ABSOLUTE)
        self.assertDictEqual(expected,t.tolerances_for_value(53))
    #----------------------------------------------------------------------
    def test_tolerances_for_value_percent(self):
        expected = {models.ACT_HIGH:1.02,models.ACT_LOW:0.98,models.TOL_LOW:0.99,models.TOL_HIGH:1.01}
        t = models.Tolerance(act_high=2,act_low=-2,tol_high=1,tol_low=-1,type=models.PERCENT)
        self.assertDictEqual(expected,t.tolerances_for_value(1))



#====================================================================================
class TestCategory(TestCase):
    pass

#====================================================================================
class TestTest(TestCase):

    #---------------------------------------------------------------------------
    def test_is_boolean(self):
        test = utils.create_test(name="bool",test_type=models.BOOLEAN)
        self.assertTrue(test.is_boolean())
    #----------------------------------------------------------------------
    def test_is_numerical(self):
        for t in (models.COMPOSITE, models.CONSTANT, models.SIMPLE):
            test = utils.create_test(name="num",test_type=t)
            self.assertTrue(test.is_numerical())

    #---------------------------------------------------------------------------
    def test_valid_check_test_type(self):
        test_types = (
            ("choices","foo, bar", models.MULTIPLE_CHOICE,"Multiple Choice"),
            ("constant_value",1.0,models.CONSTANT, "Constant"),
            ("calculation_procedure","result=foo",models.COMPOSITE, "Composite"),
        )
        for attr,val,ttype,display in test_types:
            test = utils.create_test(name=display,test_type=ttype)
            setattr(test,attr,val)
            test.check_test_type(getattr(test,attr),ttype,display)

    #---------------------------------------------------------------------------
    def test_invalid_check_test_type(self):
        test_types = (
            ("choices","foo,bar", models.CONSTANT,"Invalid"),
            ("constant_value",1.,models.COMPOSITE, "Constant"),
            ("calculation_procedure","result=foo",models.MULTIPLE_CHOICE, "Composite"),
            ("choices",None, models.MULTIPLE_CHOICE,"Multiple Choice"),
            ("constant_value",None,models.COMPOSITE, "Constant"),
            ("calculation_procedure",None,models.COMPOSITE, "Composite"),

        )
        for attr,val,ttype,display in test_types:
            test = utils.create_test(name=display,test_type=ttype)
            setattr(test,attr,val)
            test_type = ttype if val is None else models.SIMPLE
            errors = test.check_test_type(getattr(test,attr),test_type,display)
            self.assertTrue(len(errors)>0)
    #---------------------------------------------------------------------------
    def test_clean_calc_proc_not_needed(self):
        test = utils.create_test(test_type=models.SIMPLE)
        self.assertIsNone(test.clean_calculation_procedure())

    #---------------------------------------------------------------------------
    def test_invalid_clean_calculation_procedure(self):

        test = utils.create_test(test_type=models.COMPOSITE)

        invalid_calc_procedures = (
            "resul t = a + b",
            "_result = a + b",
            "0result = a+b",
            " result = a + b",
            "result_=foo",
            "",
            "foo = a +b",
            "foo = __import__('bar')",
        )

        for icp in invalid_calc_procedures:
            test.calculation_procedure = icp
            try:
                msg = "Passed but should have failed:\n %s" % icp
                test.clean_calculation_procedure()
            except ValidationError:
                msg = ""
            self.assertTrue(len(msg)==0,msg=msg)

    #----------------------------------------------------------------------
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
            self.assertTrue(len(msg)==0,msg=msg)

    #----------------------------------------------------------------------
    def test_clean_constant_value(self):
        test = utils.create_test(test_type=models.CONSTANT)
        self.assertRaises(ValidationError,test.clean_constant_value)
        test.constant_value = 1
        self.assertIsNone(test.clean_constant_value())

    #---------------------------------------------------------------------------
    def test_clean_mult_choice_not_needed(self):
        test = utils.create_test(test_type=models.SIMPLE)
        self.assertIsNone(test.clean_choices())

    #---------------------------------------------------------------------------
    def test_valid_mult_choice(self):
        test = utils.create_test(test_type=models.MULTIPLE_CHOICE)
        valid = ("foo, bar, baz", "foo,bar,baz","foo,\tbar")
        for v in valid:
            test.choices = v
            test.clean_choices()

        test.choices = valid[0]
        test.clean_choices()
        self.assertListEqual([(0,"foo"),(1,"bar"),(2,"baz")],test.get_choices())
    #---------------------------------------------------------------------------
    def test_invalid_mult_choice(self):
        test = utils.create_test(test_type=models.MULTIPLE_CHOICE)
        invalid = (None,""," ",)
        for i in invalid:
            test.choices = i
            self.assertRaises(ValidationError,test.clean_choices)
    #---------------------------------------------------------------------------
    def test_invalid_clean_slug(self):
        test = utils.create_test()

        invalid = ( "0 foo", "foo ", " foo" "foo bar", "foo*bar", "%foo", "foo$" )

        for i in invalid:
            test.slug = i
            try:
                msg = "Short name should have failed but passed: %s" % i
                test.clean_slug()
            except ValidationError:
                msg = ""

            self.assertTrue(len(msg)==0, msg=msg)
        test.type = models.COMPOSITE
        test.slug = ""

        self.assertRaises(ValidationError,test.clean_slug)
    #---------------------------------------------------------------------------
    def test_valid_clean_slug(self):
        test= utils.create_test()
        valid = ("foo", "f6oo", "foo6","_foo","foo_","foo_bar")
        for v in valid:
            test.slug = v
            try:
                msg = ""
                test.clean_slug()
            except ValidationError:
                msg = "Short name should have passed but failed: %s" % v
            self.assertTrue(len(msg)==0, msg=msg)
    #---------------------------------------------------------------------------
    def test_clean_fields(self):
        test = utils.create_test()
        test.clean_fields()
    #----------------------------------------------------------------------
    def test_get_choice(self):
        test = utils.create_test(test_type=models.MULTIPLE_CHOICE)
        test.choices = "a,b,c"
        self.assertEqual(test.get_choice_value(1),"b")

#============================================================================
class TestOnTestSaveSignal(TestCase):
    #---------------------------------------------------------------------------
    def test_valid_bool_check(self):
        ref = utils.create_reference(value=3)
        uti = utils.create_unit_test_info(ref=ref)
        uti.test.type = models.BOOLEAN
        self.assertRaises(ValidationError,uti.test.save)

#====================================================================================
class TestUnitTestInfo(TestCase):
    #---------------------------------------------------------------------------
    def test_percentage_ref(self):
        ref = utils.create_reference()
        tol = utils.create_tolerance()
        uti = utils.create_unit_test_info(ref=ref,tol=tol)
        tol.type = models.PERCENT
        ref.value = 0
        self.assertRaises(ValidationError,uti.clean)
    #---------------------------------------------------------------------------
    def test_boolean_ref(self):
        ref = utils.create_reference()
        uti = utils.create_unit_test_info(ref=ref)
        ref.value = 3
        uti.test.type = models.BOOLEAN
        self.assertRaises(ValidationError,uti.clean)
    #---------------------------------------------------------------------------
    def test_boolean_with_tol(self):
        ref = utils.create_reference()
        tol = utils.create_tolerance()
        uti = utils.create_unit_test_info(ref=utils.create_reference(),tol=tol)
        ref.value = 0
        uti.test.type = models.BOOLEAN
        self.assertRaises(ValidationError,uti.clean)
    #----------------------------------------------------------------------
    def test_mult_choice_with_tol(self):
        tol = models.Tolerance(type=models.MULTIPLE_CHOICE,mc_pass_choices="a")
        uti = utils.create_unit_test_info(tol=tol)
        uti.test.type = models.BOOLEAN
        self.assertRaises(ValidationError,uti.clean)

    #---------------------------------------------------------------------------
    #def test_new_list_due_date(self):
        #uti = utils.create_unit_test_info()
    #    self.assertIsNone(uti.due_date())
    #---------------------------------------------------------------------------
    #def test_due_date(self):

    #    now = timezone.now()
    #    frequency = utils.create_frequency(nom=7,due=7,overdue=9)
    #    uti = utils.create_unit_test_info(frequency=frequency)
    #    ti = utils.create_test_instance(unit_test_info=uti,work_completed=now)
    #    uti = models.UnitTestInfo.objects.get(pk=uti.pk )
    #    due = uti.due_date()
    #    self.assertEqual(due,now+timezone.timedelta(days=7))
    #---------------------------------------------------------------------------
    def test_history(self):
        td = timezone.timedelta
        now = timezone.now()
        uti = utils.create_unit_test_info()

        status = utils.create_status()

        #values purposely utils.created out of order to make sure history
        #returns in correct order (i.e. ordered by date)
        history = [
            (now+td(days=4), 5., models.NO_TOL, status),
            (now+td(days=1), 5., models.NO_TOL, status),
            (now+td(days=3), 6., models.NO_TOL, status),
            (now+td(days=2), 7., models.NO_TOL, status),
        ]

        for wc, val, _, _ in history:
            utils.create_test_instance(unit_test_info=uti,status=status,work_completed=wc,value=val)

        sorted_hist = list(sorted(history))
        self.assertListEqual(sorted_hist,uti.get_history())

        #test returns correct number of results
        self.assertListEqual(sorted_hist[-2:],uti.get_history(number=2))

    #----------------------------------------------------------------------
    def test_add_to_cycle(self):
        tl1 = utils.create_test_list("tl1")
        tl2 = utils.create_test_list("tl2")
        t1 = utils.create_test("t1")
        t2 = utils.create_test("t2")
        utils.create_test_list_membership(tl1,t1)
        utils.create_test_list_membership(tl2,t2)

        cycle = utils.create_cycle(test_lists=[tl1,tl2])

        utc = utils.create_unit_test_collection(test_collection=cycle)

        utis = models.UnitTestInfo.objects.all()

        self.assertEqual(len(utis),2)
        t3 = utils.create_test("t3")
        utils.create_test_list_membership(tl2,t3)

        utis = models.UnitTestInfo.objects.all()
        self.assertEqual(len(utis),3)
    #----------------------------------------------------------------------
    def test_readd_test(self):
        tl1 = utils.create_test_list("tl1")
        t1 = utils.create_test("t1")
        utils.create_test_list_membership(tl1,t1)
        utils.create_unit_test_collection(test_collection=tl1)
        utis = models.UnitTestInfo.objects.all()
        self.assertEqual(utis.count(),1)
        utis.delete()
        self.assertEqual(utis.count(),0)
        tl1.save()
        self.assertEqual(models.UnitTestInfo.objects.count(),1)


#====================================================================================
class TestTestListMembership(TestCase):
    pass


#====================================================================================
class TestTestList(TestCase):

    #---------------------------------------------------------------------------
    def test_get_list(self):
        tl = models.TestList()
        self.assertEqual(tl,tl.get_list())
    #---------------------------------------------------------------------------
    def test_get_next_list(self):
        tl = models.TestList()
        self.assertEqual(tl,tl.next_list(None))
    #---------------------------------------------------------------------------
    def test_first(self):
        tl = models.TestList()
        self.assertEqual(tl,tl.first())
    #---------------------------------------------------------------------------
    def test_all_tests(self):
        """"""
        tl = utils.create_test_list()
        tests = [utils.create_test(name="test %d" % i) for i in range(4)]
        for order,test in enumerate(tests):
            utils.create_test_list_membership(test_list=tl,test=test,order=order)

        self.assertSetEqual(set(tests),set(tl.all_tests()))
    #---------------------------------------------------------------------------
    def test_content_type(self):
        tl = utils.create_test_list()
        self.assertEqual(tl.content_type(),ContentType.objects.get(name="test list"))

    #---------------------------------------------------------------------------
    def test_all_lists(self):
        tl1 = utils.create_test_list(name="1")
        tl2 = utils.create_test_list(name="2")
        tl1.sublists.add(tl2)
        tl1.save()
        self.assertSetEqual(set([tl1,tl2]),set(tl1.all_lists()))

    #---------------------------------------------------------------------------
    def test_ordered_tests(self):
        tl1 = utils.create_test_list(name="1")
        tl2 = utils.create_test_list(name="2")
        t1 = utils.create_test()
        t2 = utils.create_test("test2")
        utils.create_test_list_membership(test_list=tl1,test=t1)
        utils.create_test_list_membership(test_list=tl2,test=t2)
        tl1.sublists.add(tl2)

        self.assertListEqual(list(tl1.ordered_tests()),[t1,t2])
    #---------------------------------------------------------------------------
    def test_len(self):
        self.assertEqual(1,len(utils.create_test_list()))

#====================================================================================
class TestTestListCycle(TestCase):
    #----------------------------------------------------------------------
    def setUp(self):
        super(TestTestListCycle,self).setUp()

        daily = utils.create_frequency(nom=1,due=1,overdue=1)
        status = utils.create_status()

        self.empty_cycle = utils.create_cycle(name="empty")
        utc = utils.create_unit_test_collection(test_collection=self.empty_cycle, frequency=daily)

        self.test_lists = [utils.create_test_list(name="test list %d"% i) for i in range(2)]
        self.tests = []
        for i,test_list in enumerate(self.test_lists):
            test = utils.create_test(name="test %d" %i)
            utils.create_test_list_membership(test_list,test)
            self.tests.append(test)
        self.cycle = utils.create_cycle(test_lists=self.test_lists)

        utc = utils.create_unit_test_collection(test_collection=self.cycle, frequency=daily,unit=utc.unit)



    #---------------------------------------------------------------------------
    def test_get_list(self):
        for day, test_list in enumerate(self.test_lists):
            self.assertEqual(test_list,self.cycle.get_list(day))

        self.assertFalse(self.empty_cycle.get_list())
    #---------------------------------------------------------------------------
    def test_get_next_list(self):
        first = self.cycle.first()
        next_ = self.cycle.next_list(first)
        self.assertEqual(next_,self.test_lists[1])

        next_ = self.cycle.next_list(next_)
        self.assertEqual(first,next_)

        self.assertFalse(self.empty_cycle.next_list(None))
    #---------------------------------------------------------------------------
    def test_first(self):
        self.assertEqual(self.cycle.first(),self.test_lists[0])
        self.assertFalse(self.empty_cycle.first())
    #---------------------------------------------------------------------------
    def test_all_tests(self):
        self.assertSetEqual(set(self.tests),set(self.cycle.all_tests()))
        self.assertEqual(0,self.empty_cycle.all_tests().count())
    #---------------------------------------------------------------------------
    def test_content_type(self):
        tl = utils.create_test_list()
        self.assertEqual(tl.content_type(),ContentType.objects.get(name="test list"))

    #---------------------------------------------------------------------------
    def test_all_lists(self):
        self.assertSetEqual(set(self.test_lists),set(self.cycle.all_lists()))
        self.assertFalse(self.empty_cycle.all_lists())

    #---------------------------------------------------------------------------
    def test_len(self):
        self.assertEqual(0,len(models.TestListCycle()))
        self.assertEqual(2,len(self.cycle))
        self.assertEqual(0,len(self.empty_cycle))

#============================================================================
class TestUnitTestCollection(TestCase):

    #---------------------------------------------------------------------------
    def test_manager_by_unit(self):
        utc = utils.create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.by_unit(utc.unit)), [utc] )
    #---------------------------------------------------------------------------
    def test_manager_by_frequency(self):
        utc = utils.create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.by_frequency(utc.frequency)), [utc] )
    #---------------------------------------------------------------------------
    def test_manager_by_unit_frequency(self):
        utc = utils.create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.by_unit_frequency(utc.unit,utc.frequency)), [utc] )
    #---------------------------------------------------------------------------
    def test_manager_test_lists(self):
        utc = utils.create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.test_lists()), [utc] )


    #---------------------------------------------------------------------------
    def test_due_date(self):

        now = timezone.now()

        test = utils.create_test()
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test=test,test_list=test_list)

        daily = utils.create_frequency(nom=1,due=1,overdue=1)

        utc = utils.create_unit_test_collection(test_collection=test_list,frequency=daily)

        tli = utils.create_test_list_instance(unit_test_collection=utc,work_completed=now)

        uti = models.UnitTestInfo.objects.get(test=test,unit=utc.unit)
        ti = utils.create_test_instance(unit_test_info=uti,work_completed=now)

        tli.testinstance_set.add(ti)
        tli.save()

        utc = models.UnitTestCollection.objects.get(pk=utc.pk)

        self.assertEqual(utc.due_date(),ti.work_completed+daily.due_delta())

        tli2 = utils.create_test_list_instance(unit_test_collection=utc,work_completed=now+timezone.timedelta(days=3))

        ti2 = utils.create_test_instance(unit_test_info=uti,work_completed=now+timezone.timedelta(days=3),status=ti.status)
        tli2.testinstance_set.add(ti2)
        ti2.save()
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)

        self.assertEqual(utc.due_date(),now+timezone.timedelta(days=4))
    #---------------------------------------------------------------------------
    def test_cycle_due_date(self):
        test_lists = [utils.create_test_list(name="test list %d"% i) for i in range(2)]
        for i,test_list in enumerate(test_lists):
            test = utils.create_test(name="test %d" %i)
            utils.create_test_list_membership(test_list,test)
        cycle = utils.create_cycle(test_lists=test_lists)
        daily = utils.create_frequency(nom=1,due=1,overdue=1)
        status = utils.create_status()
        utc = utils.create_unit_test_collection(test_collection=cycle, frequency=daily)

        now = timezone.now()
        tl = utc.next_list()
        uti = models.UnitTestInfo.objects.get(test=tl.all_tests()[0],unit=utc.unit)
        ti = utils.create_test_instance(unit_test_info=uti,work_completed=now,status=status)

        tli = utils.create_test_list_instance(unit_test_collection=utc,work_completed=now)
        tli.testinstance_set.add(ti)
        tli.save()

        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertEqual(utc.due_date(),now+daily.due_delta())

        uti = models.UnitTestInfo.objects.get(test=test_lists[1].tests.all()[0],unit=utc.unit)

        utils.create_test_instance(unit_test_info=uti,work_completed=now,status=status)
        self.assertEqual(utc.due_date(),now+daily.due_delta())


    #----------------------------------------------------------------------
    def test_daily_due_status(self):
        now = timezone.now()

        daily = utils.create_frequency(nom=1,due=1,overdue=1)

        utc = utils.create_unit_test_collection(frequency=daily)

        self.assertEqual(models.NOT_DUE,utc.due_status())

        daily_statuses = (
            (-2,models.OVERDUE),
            (-1,models.OVERDUE),
            (0, models.NOT_DUE),
            (1,models.NOT_DUE)
        )
        for delta,due_status in daily_statuses:
            wc = now+timezone.timedelta(days=delta)
            tli = utils.create_test_list_instance(unit_test_collection=utc,work_completed=wc)

            utc = models.UnitTestCollection.objects.get(pk=utc.pk)
            self.assertEqual(utc.due_status(),due_status)
    #----------------------------------------------------------------------
    def test_weekly_due_status(self):
        now = timezone.now()

        weekly = utils.create_frequency(nom=7,due=7,overdue=9)
        utc = utils.create_unit_test_collection(frequency=weekly)

        self.assertEqual(models.NOT_DUE,utc.due_status())

        weekly_statuses = (
            (-10,models.OVERDUE),
            (-8,models.DUE),
            (-7,models.DUE),
            (-6, models.NOT_DUE),
            (1,models.NOT_DUE)
        )
        for delta,due_status in weekly_statuses:
            wc = now+timezone.timedelta(days=delta)
            tli = utils.create_test_list_instance(unit_test_collection=utc,work_completed=wc)
            utc = models.UnitTestCollection.objects.get(pk=utc.pk)
            self.assertEqual(utc.due_status(),due_status)
    #----------------------------------------------------------------------
    def test_last_done_date(self):
        now = timezone.now()
        utc = utils.create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())
        tli = utils.create_test_list_instance(unit_test_collection=utc,work_completed=now)
        test = utils.create_test(name="tester")
        utils.create_test_list_membership(tli.test_list,test)

        uti = models.UnitTestInfo.objects.get(test=test,unit=utc.unit)

        ti = utils.create_test_instance(unit_test_info=uti,work_completed=now)
        ti.test_list_instance = tli
        ti.save()
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertEqual(now,utc.last_done_date())

    #----------------------------------------------------------------------
    def test_unreviewed_instances(self):
        utc = utils.create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        test = utils.create_test(name="tester")
        utils.create_test_list_membership(tli.test_list,test)
        #uti = utils.create_unit_test_info(test=test,unit=utc.unit,frequency=utc.frequency)
        uti = models.UnitTestInfo.objects.get(test=test,unit=utc.unit)
        ti = utils.create_test_instance(unit_test_info=uti)
        ti.test_list_instance = tli
        ti.save()
        self.assertEqual([tli],list(utc.unreviewed_instances()))
    #----------------------------------------------------------------------
    def test_last_completed_instance(self):
        utc = utils.create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())

        test = utils.create_test(name="tester")
        utils.create_test_list_membership(utc.tests_object,test)

        self.assertIsNone(utc.last_instance)

        uti = models.UnitTestInfo.objects.get(test=test,unit=utc.unit)
        tli = utils.create_test_list_instance(unit_test_collection=utc)
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        ti = utils.create_test_instance(unit_test_info=uti)
        ti.test_list_instance = tli
        ti.save()
        self.assertEqual(tli,utc.last_instance)
    #----------------------------------------------------------------------
    def test_unreview_test_instances(self):
        utc = utils.create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())

        test = utils.create_test(name="tester")
        utils.create_test_list_membership(utc.tests_object,test)

        self.assertIsNone(utc.last_instance)

        tli = utils.create_test_list_instance(unit_test_collection=utc)
        uti = models.UnitTestInfo.objects.get(test=test,unit=utc.unit)
        ti = utils.create_test_instance(unit_test_info=uti)
        ti.test_list_instance = tli
        ti.save()
        self.assertEqual([ti],list(utc.unreviewed_test_instances()))
    #---------------------------------------------------------------------------
    def test_history(self):
        td = timezone.timedelta
        now = timezone.now()
        utc = utils.create_unit_test_collection()

        status = utils.create_status()

        #values purposely utils.created out of order to make sure history
        #returns in correct order (i.e. ordered by date)
        history = [
            now+td(days=4), now+td(days=1), now+td(days=3), now+td(days=2),
        ]

        for wc in history:
            tli = utils.create_test_list_instance(unit_test_collection=utc,work_completed=wc)

        sorted_hist = list(sorted(history))
        dates = [x.work_completed for x in utc.history()]
        self.assertEqual(sorted_hist,dates)

        limited_dates = [x.work_completed for x in utc.history(number=2)]
        #test returns correct number of results
        self.assertListEqual(sorted_hist[-2:],limited_dates)
    #----------------------------------------------------------------------
    def test_test_list_next_list(self):

        utc = utils.create_unit_test_collection()

        self.assertEqual(utc.next_list(),utc.tests_object)

        tli = utils.create_test_list_instance(unit_test_collection=utc)
        self.assertEqual(utc.next_list(),utc.tests_object)


    #----------------------------------------------------------------------
    def test_cycle_next_list(self):

        test_lists = [utils.create_test_list(name="test list %d"% i) for i in range(2)]
        for i,test_list in enumerate(test_lists):
            test = utils.create_test(name="test %d" %i)
            utils.create_test_list_membership(test_list,test)

        cycle = utils.create_cycle(test_lists=test_lists)
        utc = utils.create_unit_test_collection(test_collection=cycle)

        self.assertEqual(utc.next_list(),test_lists[0])
        tli = utils.create_test_list_instance(unit_test_collection=utc,test_list=test_lists[0])

        #need to regrab from db since since last_instance was updated in the db
        #by signal handler
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertEqual(utc.next_list(),test_lists[1])

        tli = utils.create_test_list_instance(unit_test_collection=utc,test_list=test_lists[1])
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)

        self.assertEqual(utc.next_list(),test_lists[0])

    #----------------------------------------------------------------------
    def test_cycle_get_list(self):

        test_lists = [utils.create_test_list(name="test list %d"% i) for i in range(2)]
        for i,test_list in enumerate(test_lists):
            test = utils.create_test(name="test %d" %i)
            utils.create_test_list_membership(test_list,test)

        cycle = utils.create_cycle(test_lists=test_lists)
        utc = utils.create_unit_test_collection(test_collection=cycle)

        for i,test_list in enumerate(test_lists):
            self.assertEqual(utc.get_list(i),test_list)

        self.assertEqual(utc.get_list(),test_lists[0])

    #----------------------------------------------------------------------
    def test_name(self):
        tl = utils.create_test_list("tl1")
        utc = utils.create_unit_test_collection(test_collection=tl)
        self.assertEqual(utc.name(),str(utc))
        self.assertEqual(tl.name,utc.test_objects_name())
    #----------------------------------------------------------------------
    def test_delete_utc(self):

        utc = utils.create_unit_test_collection()

        tli = utils.create_test_list_instance(unit_test_collection=utc)
        unit = utc.unit
        tl = utc.tests_object
        utc = models.UnitTestCollection.objects.get(pk=utc.pk)
        self.assertEqual(utc.last_instance,tli)
        utc.delete()

        self.assertRaises(
            models.UnitTestCollection.DoesNotExist,
            models.UnitTestCollection.objects.get,pk=utc.pk
        )

        self.assertRaises(
            models.TestListInstance.DoesNotExist,
            models.TestListInstance.objects.get,pk=tl.pk
        )


#============================================================================
class TestSignals(TestCase):

    #----------------------------------------------------------------------
    def test_list_assigned_to_unit(self):
        test = utils.create_test(name="test")
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test_list,test)

        utc = utils.create_unit_test_collection(test_collection=test_list)

        utis = list(models.UnitTestInfo.objects.all())

        #test list on its own
        self.assertEqual(len(utis),1)
        self.assertListEqual([utc.unit,test],[utis[0].unit,utis[0].test])

        #test utis are utils.created for sublists
        sub_test = utils.create_test(name="sub")
        sub_list = utils.create_test_list(name="sublist")
        utils.create_test_list_membership(sub_list,sub_test)
        test_list.sublists.add(sub_list)
        test_list.save()

        utis = list(models.UnitTestInfo.objects.all())
        self.assertEqual(len(utis),2)
        self.assertListEqual([utc.unit,sub_test],[utis[1].unit,utis[1].test])

    def test_sublist_changed(self):
        test = utils.create_test(name="test")
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test_list,test)

        utc = utils.create_unit_test_collection(test_collection=test_list)

        #test utis are utils.created for sublists
        sub_test = utils.create_test(name="sub")
        sub_list = utils.create_test_list(name="sublist")
        utils.create_test_list_membership(sub_list,sub_test)
        test_list.sublists.add(sub_list)
        test_list.save()

        utis = list(models.UnitTestInfo.objects.all())
        self.assertEqual(len(utis),2)
        self.assertListEqual([utc.unit,sub_test],[utis[1].unit,utis[1].test])

        sub_test2 = utils.create_test(name="sub2")
        utils.create_test_list_membership(sub_list,sub_test2)
        utis = list(models.UnitTestInfo.objects.all())
        self.assertEqual(len(utis),3)

#============================================================================
class TestTestInstance(TestCase):

    #----------------------------------------------------------------------
    def test_save(self):
        ti = utils.create_test_instance()
        ti.pass_fail = None
        self.assertIsNone(ti.pass_fail)
        ti.save()
        self.assertIsNotNone(ti.pass_fail)
    #----------------------------------------------------------------------
    def test_diff(self):
        ref = utils.create_reference(value=1)
        ti = utils.create_test_instance(value=1)
        ti.reference = ref
        self.assertEqual(0,ti.difference())
    #----------------------------------------------------------------------
    def test_diff_unavailable(self):
        ti = utils.create_test_instance(value=1)
        self.assertIsNone(ti.calculate_diff())

    #----------------------------------------------------------------------
    def test_percent_diff(self):
        ref = utils.create_reference(value=1)
        ti = utils.create_test_instance(value=1.1)
        ti.reference = ref
        self.assertAlmostEqual(10,ti.percent_difference())
        ref.value=0
        self.assertRaises(ZeroDivisionError,ti.percent_difference)
    #----------------------------------------------------------------------
    def test_bool_pass_fail(self):
        test = utils.create_test(test_type=models.BOOLEAN)
        uti = models.UnitTestInfo(test=test)

        yes_ref = models.Reference(type = models.BOOLEAN,value = True,)
        no_ref = models.Reference(type = models.BOOLEAN,value = False,)

        yes_instance = models.TestInstance(value=1,unit_test_info=uti)
        no_instance = models.TestInstance(value=0,unit_test_info=uti)

        ok_tests = (
            (yes_instance,yes_ref),
            (no_instance,no_ref),
        )
        action_tests = (
            (no_instance,yes_ref),
            (yes_instance,no_ref),
        )
        for i,ref in ok_tests:
            i.reference = ref
            i.calculate_pass_fail()
            self.assertEqual(models.OK,i.pass_fail)

        for i,ref in action_tests:
            i.reference = ref
            i.calculate_pass_fail()
            self.assertEqual(models.ACTION,i.pass_fail)
    #----------------------------------------------------------------------
    def test_mult_pass_fail(self):
        test = models.Test(type=models.MULTIPLE_CHOICE,choices="a,b,c,d,e")

        t = models.Tolerance(type=models.MULTIPLE_CHOICE,mc_pass_choices="a,b",mc_tol_choices="c,d")
        uti = models.UnitTestInfo(test=test,tolerance=t)

        instance = models.TestInstance(unit_test_info=uti,tolerance=t)

        for c in (0,1):
            instance.value = c
            instance.calculate_pass_fail()
            self.assertEqual(instance.pass_fail,models.OK)

        for c in (2,3):
            instance.value = c
            instance.calculate_pass_fail()
            self.assertEqual(instance.pass_fail,models.TOLERANCE)

        for c in (4,):
            instance.value = c
            instance.calculate_pass_fail()
            self.assertEqual(instance.pass_fail,models.ACTION)

    #----------------------------------------------------------------------
    def test_absolute_pass_fail(self):
        test = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=test)
        ti = models.TestInstance(unit_test_info=uti)
        ref = models.Reference(type=models.NUMERICAL,value=100.)
        ti.reference = ref
        tol = models.Tolerance(
            type=models.ABSOLUTE,
            act_low = -3,
            tol_low = -2,
            tol_high=  2,
            act_high=  3,
        )
        ti.tolerance = tol
        tests = (
            (models.ACTION,96),
            (models.ACTION,-100),
            (models.ACTION,1E99),
            (models.ACTION,103.1),
            (models.TOLERANCE,97),
            (models.TOLERANCE,97.5),
            (models.TOLERANCE,102.1),
            (models.TOLERANCE,103),
            (models.OK,100),
            (models.OK,102),
            (models.OK,98),
        )

        for result,val in tests:
            ti.value = val
            ti.calculate_pass_fail()
            self.assertEqual(result,ti.pass_fail)

    #----------------------------------------------------------------------
    def test_edge_pass_fail(self):
        test = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=test)
        ti = models.TestInstance(unit_test_info=uti)
        ref = models.Reference(type=models.NUMERICAL,value=5.)
        ti.reference = ref
        tol = models.Tolerance(
            type=models.ABSOLUTE,
            act_low = -0.2,
            tol_low = -0.1,
            tol_high=  0.1,
            act_high=  0.2,
        )
        ti.tolerance = tol
        tests = (
            (models.ACTION,4.79999),
            (models.TOLERANCE,4.799999999999999999),
            (models.TOLERANCE,4.8),

            (models.TOLERANCE,4.89999),
            (models.OK,4.899999999999999999),
            (models.OK,4.9),


            (models.OK,5.1),
            (models.OK,5.10000000000000000000001),
            (models.TOLERANCE,5.10001),

            (models.TOLERANCE,5.2),
            (models.TOLERANCE,5.20000000000000000000001),
            (models.ACTION,5.20001),
        )

        for result,val in tests:
            ti.value = val
            ti.calculate_pass_fail()
            self.assertEqual(result,ti.pass_fail)


    #----------------------------------------------------------------------
    def test_percent_pass_fail(self):
        test = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=test)
        ti = models.TestInstance(unit_test_info=uti)

        ti.reference = models.Reference(type=models.NUMERICAL,value=100.)
        ti.tolerance = models.Tolerance(
            type=models.PERCENT,
            act_low = -3,
            tol_low = -2,
            tol_high=  2,
            act_high=  3,
        )

        tests = (
            (models.ACTION,96),
            (models.ACTION,-100),
            (models.ACTION,1E99),
            (models.ACTION,103.1),
            (models.TOLERANCE,97),
            (models.TOLERANCE,97.5),
            (models.TOLERANCE,102.1),
            (models.TOLERANCE,103),
            (models.OK,100),
            (models.OK,102),
            (models.OK,98),
        )

        for result,val in tests:
            ti.value = val
            ti.calculate_pass_fail()
            self.assertEqual(result,ti.pass_fail)

    #----------------------------------------------------------------------
    def test_skipped(self):
        tol = models.Tolerance(type=models.PERCENT,)
        ti = models.TestInstance(skipped=True)
        ti.calculate_pass_fail()
        self.assertEqual(models.NOT_DONE,ti.pass_fail)
    #----------------------------------------------------------------------
    def test_in_progress(self):
        ti = utils.create_test_instance()
        ti.in_progress = True
        ti.save()

        self.assertEqual(models.TestInstance.objects.in_progress()[0],ti)

    #----------------------------------------------------------------------
    def test_bool_display_value(self):
        t = models.Test(type=models.BOOLEAN)
        uti = models.UnitTestInfo(test=t)

        ti = models.TestInstance(unit_test_info=uti,value=1)
        self.assertEqual("Yes",ti.value_display())

        ti = models.TestInstance(unit_test_info=uti,value=0)
        self.assertEqual("No",ti.value_display())


    #----------------------------------------------------------------------
    def test_mc_display_value(self):
        t = models.Test(type=models.MULTIPLE_CHOICE,choices="a,b,c")
        uti = models.UnitTestInfo(test=t)

        ti = models.TestInstance(unit_test_info=uti,value=0)
        self.assertEqual("a",ti.value_display())
        ti = models.TestInstance(unit_test_info=uti,value=1)
        self.assertEqual("b",ti.value_display())
        ti = models.TestInstance(unit_test_info=uti,value=2)
        self.assertEqual("c",ti.value_display())

    #----------------------------------------------------------------------
    def test_reg_display_value(self):
        t = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=t)

        ti = models.TestInstance(unit_test_info=uti,value=0)
        self.assertEqual("0",ti.value_display())

        ti.skipped = True
        self.assertEqual("Skipped",ti.value_display())

        ti.skipped = False
        ti.value = None
        self.assertEqual("Not Done",ti.value_display())

    #----------------------------------------------------------------------
    def test_diff_display_no_value(self):
        t = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=t)

        ti = models.TestInstance(unit_test_info=uti,value=0)
        self.assertEqual("",ti.diff_display())
    #----------------------------------------------------------------------
    def test_diff_display_absolute(self):
        t = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=t)

        tol = models.Tolerance(act_high=2,act_low=-2,tol_high=1,tol_low=-1,type=models.ABSOLUTE)
        ref = models.Reference(type=models.NUMERICAL,value=100.)

        ti = models.TestInstance(unit_test_info=uti,value=0,reference=ref,tolerance=tol)
        self.assertEqual("-100",ti.diff_display())

    #----------------------------------------------------------------------
    def test_diff_display_percent(self):
        t = models.Test(type=models.SIMPLE)
        uti = models.UnitTestInfo(test=t)

        tol = models.Tolerance(act_high=2,act_low=-2,tol_high=1,tol_low=-1,type=models.PERCENT)
        ref = models.Reference(type=models.NUMERICAL,value=1.)

        ti = models.TestInstance(unit_test_info=uti,value=0.995,reference=ref,tolerance=tol)
        self.assertEqual("-0.5%",ti.diff_display())



#============================================================================
class TestTestListInstance(TestCase):

    #----------------------------------------------------------------------
    def setUp(self):
        self.tests = []

        self.ref = models.Reference(type=models.NUMERICAL,value=100.)
        self.tol = models.Tolerance( type=models.PERCENT, act_low = -3, tol_low =-2, tol_high= 2, act_high= 3)
        self.values = [None, None,96,97,100,100]

        self.statuses = [utils.create_status(name="status%d"%x,slug="status%d"%x) for x in range(len(self.values))]


        self.test_list = utils.create_test_list()
        for i in range(6):
            test = utils.create_test(name="name%d"%i)
            self.tests.append(test)
            utils.create_test_list_membership(self.test_list,test)

        self.unit_test_collection = utils.create_unit_test_collection(test_collection=self.test_list)

        self.test_list_instance = self.create_test_list_instance()
    #----------------------------------------------------------------------
    def create_test_list_instance(self):
        utc = self.unit_test_collection

        tli = utils.create_test_list_instance(unit_test_collection=utc)

        for i,(v,test,status) in enumerate(zip(self.values,self.tests,self.statuses)):
            uti = models.UnitTestInfo.objects.get(test=test,unit=utc.unit)
            ti = utils.create_test_instance(unit_test_info=uti,value=v,status=status)
            ti.reference = self.ref
            ti.tolerance = self.tol
            ti.test_list_instance = tli
            if i == 0:
                ti.skipped = True
            elif i == 1:
                ti.tolerance = None
                ti.reference = None

            ti.save()
        tli.save()
        return tli

    #----------------------------------------------------------------------
    def test_pass_fail(self):

        pf_status = self.test_list_instance.pass_fail_status()
        for pass_fail, _, tests in pf_status:
            if pass_fail == models.OK:
                self.assertTrue(len(tests)==2)
            else:
                self.assertTrue(len(tests)==1)

    #----------------------------------------------------------------------
    def test_review_status(self):

        status = self.test_list_instance.status()
        for stat,tests in self.test_list_instance.status():
            self.assertEqual(len(tests),1)

    #----------------------------------------------------------------------
    def test_unreviewed_instances(self):

        self.assertSetEqual(
            set(self.test_list_instance.unreviewed_instances()),
            set(models.TestInstance.objects.all())
        )
    #----------------------------------------------------------------------
    def test_tolerance_tests(self):
        self.assertEqual(1,self.test_list_instance.tolerance_tests().count())
    #----------------------------------------------------------------------
    def test_failing_tests(self):
        self.assertEqual(1,self.test_list_instance.tolerance_tests().count())
    #----------------------------------------------------------------------
    def test_in_progress(self):
        self.test_list_instance.in_progress = True
        self.test_list_instance.save()
        self.assertEqual(
            models.TestListInstance.objects.in_progress()[0],
            self.test_list_instance
        )

    #----------------------------------------------------------------------
    def test_deleted_signal_tis_deleted(self):
        self.test_list_instance.delete()
        self.assertEqual(models.TestInstance.objects.count(),0)

    #----------------------------------------------------------------------
    def test_deleted_signal_last_instance_updated(self):

        tli = self.create_test_list_instance()
        self.unit_test_collection = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(self.unit_test_collection.last_instance,tli)

        tli.delete()
        self.unit_test_collection = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(self.unit_test_collection.last_instance,self.test_list_instance)

        self.test_list_instance.delete()
        self.unit_test_collection = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(self.unit_test_collection.last_instance,None)

    #----------------------------------------------------------------------
    def test_deleted_signal_uti_last_instance_updated(self):
        tli = self.create_test_list_instance()
        utc = self.unit_test_collection

        for test in self.tests:
            uti = models.UnitTestInfo.objects.get(test=test,unit=utc.unit)
            self.assertIn(uti.last_instance,tli.testinstance_set.all())

        tli.delete()

        for test in self.tests:
            uti = models.UnitTestInfo.objects.get(test=test,unit=utc.unit)
            self.assertIn(uti.last_instance,self.test_list_instance.testinstance_set.all())

        self.test_list_instance.delete()
        for test in self.tests:
            uti = models.UnitTestInfo.objects.get(test=test,unit=utc.unit)
            self.assertIsNone(uti.last_instance)

    #----------------------------------------------------------------------
    def test_input_later(self):
        tli = self.create_test_list_instance()
        utc = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(utc.last_instance, tli)

        tli.work_completed = timezone.now()-timezone.timedelta(days=1)
        tli.save()

        utc = models.UnitTestCollection.objects.get(pk=self.unit_test_collection.pk)
        self.assertEqual(utc.last_instance, self.test_list_instance)



if __name__ == "__main__":
    setup_test_environment()
    unittest.main()