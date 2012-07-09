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

#----------------------------------------------------------------------
def create_user(is_staff=True,is_superuser=True,uname="user",pwd="password"):

    u,_ = User.objects.get_or_create(
        username=uname,is_staff=is_staff,is_superuser=is_superuser,
    )
    u.set_password(pwd)
    u.save()
    return u
#----------------------------------------------------------------------
def create_category(name="cat"):
    c,_ = models.Category.objects.get_or_create(name=name,slug="cat",description="cat")
    c.save()
    return c
#----------------------------------------------------------------------
def create_status(name="status",slug="status",is_default=True):
    status = models.TestInstanceStatus(name=name,slug=slug,is_default=is_default,requires_review=True)
    status.save()
    return status

#----------------------------------------------------------------------
def create_test(name="test",test_type=models.SIMPLE):
    user = create_user()
    test = models.Test(
        name = name,
        slug=name,
        description = "desc",
        type = test_type,
        category = create_category(),
        created_by = user,
        modified_by = user,
    )
    test.save()
    return test
#----------------------------------------------------------------------
def create_test_list(name="test_list"):
    user = create_user()
    test_list = models.TestList(
        name = name,
        slug=name,
        description = "desc",
        created_by = user,
        modified_by = user,
    )
    test_list.save()
    return test_list
#----------------------------------------------------------------------
def create_test_list_instance(unit=None,test_list=None,work_completed=None,created_by=None):
    if unit is None: unit = create_unit()
    if test_list is None: test_list = create_test_list()
    if work_completed is None: work_completed = timezone.now()
    if created_by is None: created_by = create_user()


    tli = models.TestListInstance(
        test_list=test_list,
        unit=unit,
        created_by=created_by,
        modified_by=created_by,
        work_completed=work_completed
    )
    tli.save()
    return tli

#----------------------------------------------------------------------
def create_cycle(test_lists=None,name="cycle"):
    user = create_user()
    cycle = models.TestListCycle(
        name=name,
        slug=name,
        created_by = user,
        modified_by = user
    )
    cycle.save()
    if test_lists:
        for order, test_list in enumerate(test_lists):
            tlcm = models.TestListCycleMembership(
                test_list=test_list,
                cycle=cycle,
                order=order
            )
            tlcm.save()

    return cycle

#----------------------------------------------------------------------
def create_test_list_membership(test_list,test,order=0):
    tlm = models.TestListMembership( test_list = test_list, test= test, order= order)
    tlm.save()
    return tlm

#----------------------------------------------------------------------
def create_test_instance(test=None,unit=None,value=1., created_by=None,work_completed=None,status=None):
    if unit is None: unit = create_unit()
    if test is None: test = create_test()
    if work_completed is None: work_completed = timezone.now()
    if created_by is None: created_by = create_user()
    if status is None: status = create_status()

    ti = models.TestInstance(
        test=test,
        unit=unit,
        value=value,
        created_by=created_by,
        modified_by=created_by,
        status=status,
        work_completed=work_completed,
    )

    ti.save()
    return ti
#----------------------------------------------------------------------
def create_modality(energy=6,particle=PHOTON):
    m = Modality(type=particle,energy=energy)
    m.save()
    return m
#----------------------------------------------------------------------
def create_unit_type(name="utype",vendor="vendor",model="model"):
    ut = UnitType(name=name,vendor=vendor, model=model)
    ut.save()
    return ut

#----------------------------------------------------------------------
def create_unit(name="unit", number=1):
    u = Unit(name=name,number=number)
    u.type = create_unit_type()
    u.save()
    u.modalities.add(create_modality())
    u.save()
    return u
#----------------------------------------------------------------------
def create_reference(name="ref",ref_type=models.NUMERICAL,value=1,created_by=None):
    if created_by is None: created_by = create_user()

    r = models.Reference(
        name=name,type=ref_type,value=value,
        created_by=created_by, modified_by=created_by
    )
    r.save()
    return r
#----------------------------------------------------------------------
def create_tolerance(tol_type=models.ABSOLUTE,act_low=-2,tol_low=-1,tol_high=1,act_high=2,created_by=None):
    if created_by is None: created_by = create_user()
    tol = models.Tolerance(
        type=models.ABSOLUTE,
        act_low = act_low,
        tol_low = tol_low,
        tol_high=  tol_high,
        act_high=  act_high,
        created_by=created_by,modified_by=created_by
    )
    tol.save()
    return tol

#----------------------------------------------------------------------
def create_group(name="group"):
    g = Group(name=name)
    g.save()
    return g
#----------------------------------------------------------------------
def create_frequency(name="freq",slug="freq",nom=1,due=1,overdue=1):
    f = models.Frequency(
        name=name,slug=slug,
        nominal_interval=nom, due_interval=due, overdue_interval=overdue
    )
    f.save()
    return f
#----------------------------------------------------------------------
def create_unit_test_info(unit=None,test=None,frequency=None,assigned_to=None,ref=None,tol=None,active=True):
    if unit is None: unit = create_unit()
    if test is None: test = create_test()
    if frequency is None: frequency = create_frequency()
    if assigned_to is None: assigned_to = create_group()


    uti = models.UnitTestInfo(
        unit=unit,
        test=test,
        frequency=frequency,
        reference=ref,
        tolerance=tol,
        assigned_to=assigned_to,
        active=active
    )
    uti.save()
    return uti

#----------------------------------------------------------------------
def create_unit_test_collection(unit=None,frequency=None,test_collection=None):

    if unit is None: unit = create_unit()
    if test_collection is None: test_collection = create_test_list()
    if frequency is None: frequency = create_frequency()

    utc =  models.UnitTestCollection(
        unit = unit,
        object_id = test_collection.pk,
        content_type = ContentType.objects.get_for_model(test_collection),
        frequency = frequency
    )

    utc.save()
    return utc

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
            create_frequency(name=t,slug=s,nom=nom,due=due,overdue=overdue)
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
            f = create_frequency(name=t,slug=s,nom=nom,due=due,overdue=overdue)
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
        u = create_user()
        r = models.Reference(
            name="bool",type=models.BOOLEAN,value=3,
            created_by=u, modified_by=u
        )
        self.assertRaises(ValidationError,r.clean_fields)

#====================================================================================
class TestTolerance(TestCase):
    pass

#====================================================================================
class TestCategory(TestCase):
    pass

#====================================================================================
class TestTest(TestCase):
    #---------------------------------------------------------------------------
    def test_set_references(self):
        """make sure set references links in admin work"""
        user = create_user()
        test = create_test()

        set_ref_link = test.set_references()
        self.client.login(username="user",password="password")

        for url in re.findall('href="(.*?)"',set_ref_link):
            response = self.client.get(url)
            self.assertEqual(response.status_code,200)

    #---------------------------------------------------------------------------
    def test_is_boolean(self):
        test = create_test(name="bool",test_type=models.BOOLEAN)
        self.assertTrue(test.is_boolean())

    #---------------------------------------------------------------------------
    def test_valid_check_test_type(self):
        test_types = (
            ("choices","foo, bar", models.MULTIPLE_CHOICE,"Multiple Choice"),
            ("constant_value",1.0,models.CONSTANT, "Constant"),
            ("calculation_procedure","result=foo",models.COMPOSITE, "Composite"),
        )
        for attr,val,ttype,display in test_types:
            test = create_test(name=display,test_type=ttype)
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
            test = create_test(name=display,test_type=ttype)
            setattr(test,attr,val)
            test_type = ttype if val is None else models.SIMPLE
            errors = test.check_test_type(getattr(test,attr),test_type,display)
            self.assertTrue(len(errors)>0)
    #---------------------------------------------------------------------------
    def test_clean_calc_proc_not_needed(self):
        test = create_test(test_type=models.SIMPLE)
        self.assertIsNone(test.clean_calculation_procedure())

    #---------------------------------------------------------------------------
    def test_invalid_clean_calculation_procedure(self):

        test = create_test(test_type=models.COMPOSITE)

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
        test = create_test(test_type=models.COMPOSITE)

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
        test = create_test(test_type=models.CONSTANT)
        self.assertRaises(ValidationError,test.clean_constant_value)
        test.constant_value = 1
        self.assertIsNone(test.clean_constant_value())

    #---------------------------------------------------------------------------
    def test_clean_mult_choice_not_needed(self):
        test = create_test(test_type=models.SIMPLE)
        self.assertIsNone(test.clean_choices())

    #---------------------------------------------------------------------------
    def test_valid_mult_choice(self):
        test = create_test(test_type=models.MULTIPLE_CHOICE)
        valid = ("foo, bar, baz", "foo,bar,baz","foo,\tbar")
        for v in valid:
            test.choices = v
            test.clean_choices()

        test.choices = valid[0]
        test.clean_choices()
        self.assertListEqual([(0,"foo"),(1,"bar"),(2,"baz")],test.get_choices())
    #---------------------------------------------------------------------------
    def test_invalid_mult_choice(self):
        test = create_test(test_type=models.MULTIPLE_CHOICE)
        invalid = ("foo", "foo bar",)
        for i in invalid:
            test.choices = i
            self.assertRaises(ValidationError,test.clean_choices)
    #---------------------------------------------------------------------------
    def test_invalid_clean_slug(self):
        test = create_test()

        invalid = ( "0 foo", "foo ", " foo" "foo bar", "foo*bar", "%foo", "foo$" )

        for i in invalid:
            test.slug = i
            try:
                msg = "Short name should have failed but passed: %s" % i
                test.clean_slug()
            except ValidationError:
                msg = ""

            self.assertTrue(len(msg)==0, msg=msg)
    #---------------------------------------------------------------------------
    def test_valid_clean_slug(self):
        test= create_test()
        valid = ("foo", "f6oo", "foo6","_foo","foo_","foo_bar",)
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
        test = create_test()
        test.clean_fields()

#============================================================================
class TestOnTestSaveSignal(TestCase):
    #---------------------------------------------------------------------------
    def test_valid_bool_check(self):
        ref = create_reference(value=3)
        uti = create_unit_test_info(ref=ref)
        uti.test.type = models.BOOLEAN
        self.assertRaises(ValidationError,uti.test.save)

#====================================================================================
class TestUnitTestInfo(TestCase):
    #---------------------------------------------------------------------------
    def test_percentage_ref(self):
        ref = create_reference()
        tol = create_tolerance()
        uti = create_unit_test_info(ref=ref,tol=tol)
        tol.type = models.PERCENT
        ref.value = 0
        self.assertRaises(ValidationError,uti.clean)
    #---------------------------------------------------------------------------
    def test_boolean_ref(self):
        ref = create_reference()
        uti = create_unit_test_info(ref=ref)
        ref.value = 3
        uti.test.type = models.BOOLEAN
        self.assertRaises(ValidationError,uti.clean)
    #---------------------------------------------------------------------------
    def test_boolean_with_tol(self):
        ref = create_reference()
        tol = create_tolerance()
        uti = create_unit_test_info(ref=create_reference(),tol=tol)
        ref.value = 0
        uti.test.type = models.BOOLEAN
        self.assertRaises(ValidationError,uti.clean)
    #---------------------------------------------------------------------------
    def test_new_list_due_date(self):
        uti = create_unit_test_info()
        self.assertIsNone(uti.due_date())
    #---------------------------------------------------------------------------
    def test_due_date(self):
        now = timezone.now()
        frequency = create_frequency(nom=7,due=7,overdue=9)
        uti = create_unit_test_info(frequency=frequency)
        ti = create_test_instance(test=uti.test,unit=uti.unit,work_completed=now)
        due = uti.due_date()
        self.assertEqual(due,now+timezone.timedelta(days=7))
    #---------------------------------------------------------------------------
    def test_history(self):
        td = timezone.timedelta
        now = timezone.now()
        uti = create_unit_test_info()

        status = create_status()

        #values purposely created out of order to make sure history
        #returns in correct order (i.e. ordered by date)
        history = [
            (now+td(days=4), 5., models.NO_TOL, status),
            (now+td(days=1), 5., models.NO_TOL, status),
            (now+td(days=3), 6., models.NO_TOL, status),
            (now+td(days=2), 7., models.NO_TOL, status),
        ]

        for wc, val, _, _ in history:
            create_test_instance(test=uti.test,unit=uti.unit,status=status,work_completed=wc,value=val)

        sorted_hist = list(sorted(history))
        self.assertListEqual(sorted_hist,uti.history())

        #test returns correct number of results
        self.assertListEqual(sorted_hist[-2:],uti.history(number=2))



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
        tl = create_test_list()
        tests = [create_test(name="test %d" % i) for i in range(4)]
        for order,test in enumerate(tests):
            create_test_list_membership(test_list=tl,test=test,order=order)

        self.assertSetEqual(set(tests),set(tl.all_tests()))
    #---------------------------------------------------------------------------
    def test_content_type(self):
        tl = create_test_list()
        self.assertEqual(tl.content_type(),ContentType.objects.get(name="test list"))

    #---------------------------------------------------------------------------
    def test_all_lists(self):
        tl1 = create_test_list(name="1")
        tl2 = create_test_list(name="2")
        tl1.sublists.add(tl2)
        tl1.save()
        self.assertSetEqual(set([tl1,tl2]),set(tl1.all_lists()))

    #---------------------------------------------------------------------------
    def test_ordered_tests(self):
        tl1 = create_test_list(name="1")
        tl2 = create_test_list(name="2")
        t1 = create_test()
        t2 = create_test("test2")
        create_test_list_membership(test_list=tl1,test=t1)
        create_test_list_membership(test_list=tl2,test=t2)
        tl1.sublists.add(tl2)

        self.assertListEqual(list(tl1.ordered_tests()),[t1,t2])
    #---------------------------------------------------------------------------
    def test_set_references_link(self):
        #user = create_user(is_staff=True,is_superuser=True,uname="user",pwd="password")

        user = create_user()
        test_list = create_test_list()
        test = create_test()
        create_test_list_membership(test_list=test_list,test=test)

        unassigned = "<em>Currently not assigned to any units</em>"
        self.assertEqual(unassigned,test_list.set_references())

        utl = create_unit_test_collection(test_collection=test_list)
        set_ref_link = utl.tests_object.set_references()

        import re
        urls = re.findall('href="(.*?)"',set_ref_link)
        self.assertEqual(len(urls),1)
        self.client.login(username="user",password="password")
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code,200)
    #---------------------------------------------------------------------------
    def test_len(self):
        self.assertEqual(1,len(create_test_list()))

#====================================================================================
class TestTestListCycle(TestCase):
    #----------------------------------------------------------------------
    def setUp(self):
        super(TestTestListCycle,self).setUp()

        daily = create_frequency(nom=1,due=1,overdue=1)
        status = create_status()

        self.empty_cycle = create_cycle(name="empty")
        utc = create_unit_test_collection(test_collection=self.empty_cycle, frequency=daily)

        self.test_lists = [create_test_list(name="test list %d"% i) for i in range(2)]
        self.tests = []
        for i,test_list in enumerate(self.test_lists):
            test = create_test(name="test %d" %i)
            create_test_list_membership(test_list,test)
            self.tests.append(test)
        self.cycle = create_cycle(test_lists=self.test_lists)

        utc = create_unit_test_collection(test_collection=self.cycle, frequency=daily,unit=utc.unit)



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
        tl = create_test_list()
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
        utc = create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.by_unit(utc.unit)), [utc] )
    #---------------------------------------------------------------------------
    def test_manager_by_frequency(self):
        utc = create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.by_frequency(utc.frequency)), [utc] )
    #---------------------------------------------------------------------------
    def test_manager_by_unit_frequency(self):
        utc = create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.by_unit_frequency(utc.unit,utc.frequency)), [utc] )
    #---------------------------------------------------------------------------
    def test_manager_test_lists(self):
        utc = create_unit_test_collection()
        self.assertListEqual(list(models.UnitTestCollection.objects.test_lists()), [utc] )


    #---------------------------------------------------------------------------
    def test_due_date(self):

        now = timezone.now()

        test = create_test()
        test_list = create_test_list()
        create_test_list_membership(test=test,test_list=test_list)

        daily = create_frequency(nom=1,due=1,overdue=1)

        utc = create_unit_test_collection(test_collection=test_list,frequency=daily)

        ti = create_test_instance(test=test,work_completed=now,unit=utc.unit)
        self.assertEqual(utc.due_date(),ti.work_completed+daily.due_delta())

        ti2 = create_test_instance(test=test,work_completed=now+timezone.timedelta(days=3), unit=utc.unit,status=ti.status)

        self.assertEqual(utc.due_date(),now+timezone.timedelta(days=4))
    #---------------------------------------------------------------------------
    def test_cycle_due_date(self):
        test_lists = [create_test_list(name="test list %d"% i) for i in range(2)]
        for i,test_list in enumerate(test_lists):
            test = create_test(name="test %d" %i)
            create_test_list_membership(test_list,test)
        cycle = create_cycle(test_lists=test_lists)
        daily = create_frequency(nom=1,due=1,overdue=1)
        status = create_status()
        utc = create_unit_test_collection(test_collection=cycle, frequency=daily)

        now = timezone.now()
        create_test_instance(test=test_lists[0].tests.all()[0],unit=utc.unit,work_completed=now,status=status)
        self.assertEqual(utc.due_date(),now+daily.due_delta())

        create_test_instance(test=test_lists[1].tests.all()[0],unit=utc.unit,work_completed=now,status=status)
        self.assertEqual(utc.due_date(),now+daily.due_delta())


    #----------------------------------------------------------------------
    def test_daily_due_status(self):
        now = timezone.now()

        daily = create_frequency(nom=1,due=1,overdue=1)

        utc = create_unit_test_collection(frequency=daily)

        self.assertEqual(models.NOT_DUE,utc.due_status())

        daily_statuses = (
            (-2,models.OVERDUE),
            (-1,models.OVERDUE),
            (0, models.NOT_DUE),
            (1,models.NOT_DUE)
        )
        for delta,due_status in daily_statuses:
            wc = now+timezone.timedelta(days=delta)
            tli = create_test_list_instance(unit=utc.unit,test_list=utc.tests_object,work_completed=wc)
            self.assertEqual(utc.due_status(),due_status)
    #----------------------------------------------------------------------
    def test_weekly_due_status(self):
        now = timezone.now()

        weekly = create_frequency(nom=7,due=7,overdue=9)
        utc = create_unit_test_collection(frequency=weekly)

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
            tli = create_test_list_instance(unit=utc.unit,test_list=utc.tests_object,work_completed=wc)
            self.assertEqual(utc.due_status(),due_status)
    #----------------------------------------------------------------------
    def test_last_done_date(self):
        now = timezone.now()
        utc = create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())
        tli = create_test_list_instance(unit=utc.unit,test_list=utc.tests_object,work_completed=now)
        test = create_test(name="tester")
        create_test_list_membership(tli.test_list,test)

        ti = create_test_instance(test=test,unit=utc.unit,work_completed=now)
        ti.test_list_instance = tli
        ti.save()
        self.assertEqual(now,utc.last_done_date())

    #----------------------------------------------------------------------
    def test_unreviewed_instances(self):
        utc = create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())
        tli = create_test_list_instance(unit=utc.unit,test_list=utc.tests_object)
        test = create_test(name="tester")
        create_test_list_membership(tli.test_list,test)

        ti = create_test_instance(test=test,unit=utc.unit)
        ti.test_list_instance = tli
        ti.save()
        self.assertEqual([tli],list(utc.unreviewed_instances()))
    #----------------------------------------------------------------------
    def test_last_completed_instance(self):
        utc = create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())

        test = create_test(name="tester")
        create_test_list_membership(utc.tests_object,test)

        self.assertIsNone(utc.last_completed_instance())

        tli = create_test_list_instance(unit=utc.unit,test_list=utc.tests_object)
        ti = create_test_instance(test=test,unit=utc.unit)
        ti.test_list_instance = tli
        ti.save()
        self.assertEqual(tli,utc.last_completed_instance())
    #----------------------------------------------------------------------
    def test_unreview_test_instances(self):
        utc = create_unit_test_collection()
        self.assertFalse(utc.unreviewed_instances())

        test = create_test(name="tester")
        create_test_list_membership(utc.tests_object,test)

        self.assertIsNone(utc.last_completed_instance())

        tli = create_test_list_instance(unit=utc.unit,test_list=utc.tests_object)
        ti = create_test_instance(test=test,unit=utc.unit)
        ti.test_list_instance = tli
        ti.save()
        self.assertEqual([ti],list(utc.unreviewed_test_instances()))
    #---------------------------------------------------------------------------
    def test_history(self):
        td = timezone.timedelta
        now = timezone.now()
        utc = create_unit_test_collection()

        status = create_status()

        #values purposely created out of order to make sure history
        #returns in correct order (i.e. ordered by date)
        history = [
            now+td(days=4), now+td(days=1), now+td(days=3), now+td(days=2),
        ]

        for wc in history:
            tli = create_test_list_instance(unit=utc.unit,test_list=utc.tests_object,work_completed=wc)

        sorted_hist = list(sorted(history))
        dates = [x.work_completed for x in utc.history()]
        self.assertEqual(sorted_hist,dates)

        limited_dates = [x.work_completed for x in utc.history(number=2)]
        #test returns correct number of results
        self.assertListEqual(sorted_hist[-2:],limited_dates)
    #----------------------------------------------------------------------
    def test_test_list_next_list(self):

        utc = create_unit_test_collection()

        self.assertEqual(utc.next_list(),utc.tests_object)

        tli = create_test_list_instance(unit=utc.unit,test_list=utc.tests_object)
        self.assertEqual(utc.next_list(),utc.tests_object)


    #----------------------------------------------------------------------
    def test_cycle_next_list(self):

        test_lists = [create_test_list(name="test list %d"% i) for i in range(2)]
        for i,test_list in enumerate(test_lists):
            test = create_test(name="test %d" %i)
            create_test_list_membership(test_list,test)

        cycle = create_cycle(test_lists=test_lists)
        utc = create_unit_test_collection(test_collection=cycle)

        self.assertEqual(utc.next_list(),test_lists[0])

        tli = create_test_list_instance(unit=utc.unit,test_list=test_lists[0])
        self.assertEqual(utc.next_list(),test_lists[1])

        tli = create_test_list_instance(unit=utc.unit,test_list=test_lists[1])
        self.assertEqual(utc.next_list(),test_lists[0])

    #----------------------------------------------------------------------
    def test_name(self):
        utc = create_unit_test_collection()
        self.assertEqual(utc.name(),str(utc))


#============================================================================
class TestSignals(TestCase):

    #----------------------------------------------------------------------
    def test_list_assigned_to_unit(self):
        test = create_test(name="test")
        test_list = create_test_list()
        create_test_list_membership(test_list,test)

        utc = create_unit_test_collection(test_collection=test_list)

        utis = list(models.UnitTestInfo.objects.all())

        #test list on its own
        self.assertEqual(len(utis),1)
        self.assertListEqual([utc.unit,test],[utis[0].unit,utis[0].test])

        #test utis are created for sublists
        sub_test = create_test(name="sub")
        sub_list = create_test_list(name="sublist")
        create_test_list_membership(sub_list,sub_test)
        test_list.sublists.add(sub_list)
        test_list.save()

        utis = list(models.UnitTestInfo.objects.all())
        self.assertEqual(len(utis),2)
        self.assertListEqual([utc.unit,sub_test],[utis[1].unit,utis[1].test])

    def test_sublist_changed(self):
        test = create_test(name="test")
        test_list = create_test_list()
        create_test_list_membership(test_list,test)

        utc = create_unit_test_collection(test_collection=test_list)

        #test utis are created for sublists
        sub_test = create_test(name="sub")
        sub_list = create_test_list(name="sublist")
        create_test_list_membership(sub_list,sub_test)
        test_list.sublists.add(sub_list)
        test_list.save()

        utis = list(models.UnitTestInfo.objects.all())
        self.assertEqual(len(utis),2)
        self.assertListEqual([utc.unit,sub_test],[utis[1].unit,utis[1].test])

        sub_test2 = create_test(name="sub2")
        create_test_list_membership(sub_list,sub_test2)
        utis = list(models.UnitTestInfo.objects.all())
        self.assertEqual(len(utis),3)

#============================================================================
class TestTestInstance(TestCase):

    #----------------------------------------------------------------------
    def test_save(self):
        ti = create_test_instance()
        ti.pass_fail = None
        self.assertIsNone(ti.pass_fail)
        ti.save()
        self.assertIsNotNone(ti.pass_fail)
    #----------------------------------------------------------------------
    def test_diff(self):
        ref = create_reference(value=1)
        ti = create_test_instance(value=1)
        ti.reference = ref
        self.assertEqual(0,ti.difference())
    #----------------------------------------------------------------------
    def test_percent_diff(self):
        ref = create_reference(value=1)
        ti = create_test_instance(value=1.1)
        ti.reference = ref
        self.assertAlmostEqual(10,ti.percent_difference())
        ref.value=0
        self.assertRaises(ValueError,ti.percent_difference)
    #----------------------------------------------------------------------
    def test_bool_pass_fail(self):
        test = create_test(test_type=models.BOOLEAN)
        yes_ref = models.Reference(type = models.BOOLEAN,value = True,)
        no_ref = models.Reference(type = models.BOOLEAN,value = False,)

        yes_instance = models.TestInstance(value=1,test=test)
        no_instance = models.TestInstance(value=0,test=test)

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
    def test_absolute_pass_fail(self):
        test = models.Test(type=models.SIMPLE)
        ti = models.TestInstance(test=test)
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
    def test_percent_pass_fail(self):
        test = models.Test(type=models.SIMPLE)
        ti = models.TestInstance(test=test)
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

#============================================================================
class TestTestListInstance(TestCase):

    #----------------------------------------------------------------------
    def setUp(self):
        tests = []

        ref = models.Reference(type=models.NUMERICAL,value=100.)
        tol = models.Tolerance( type=models.PERCENT, act_low = -3, tol_low =-2, tol_high= 2, act_high= 3)


        self.test_list = create_test_list()
        for i in range(6):
            test = create_test(name="name%d"%i)
            tests.append(test)
            create_test_list_membership(self.test_list,test)

        utc = create_unit_test_collection(test_collection=self.test_list)

        self.test_list_instance = create_test_list_instance(unit=utc.unit,test_list=self.test_list)

        values = [None, None,96,97,100,100]
        self.statuses = [create_status(name="status%d"%x,slug="status%d"%x) for x in range(len(values))]
        for i,(v,test,status) in enumerate(zip(values,tests,self.statuses)):
            ti = create_test_instance(test=test,unit=utc.unit,value=v,status=status)
            ti.reference = ref
            ti.tolerance = tol
            ti.test_list_instance = self.test_list_instance
            if i == 0:
                ti.skipped = True
            elif i == 1:
                ti.tolerance = None
                ti.reference = None

            ti.save()

    #----------------------------------------------------------------------
    def test_pass_fail(self):

        pf_status = self.test_list_instance.pass_fail_status()
        for pass_fail, _, tests in pf_status:
            if pass_fail == models.OK:
                self.assertTrue(len(tests)==2)
            else:
                self.assertTrue(len(tests)==1)

        formatted = "1 Not Done, 2 OK, 1 Tolerance, 1 Action, 1 No Tol Set"
        self.assertEqual(self.test_list_instance.pass_fail_status(True),formatted)

    #----------------------------------------------------------------------
    def test_review_status(self):

        status = self.test_list_instance.status()
        for stat,tests in self.test_list_instance.status():
            self.assertEqual(tests.count(),1)

        self.assertEqual(
            self.test_list_instance.status(formatted=True),
            ", ".join(["1 status%d" % x for x in range(len(self.statuses))])
        )
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


if __name__ == "__main__":
    setup_test_environment()
    unittest.main()