import coverage
coverage.start()
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import Client
from django.test.utils import setup_test_environment
from django.utils import unittest,timezone

from django.contrib.auth.models import User
from qatrack.qa import models
from qatrack.qa import *
from qatrack.units.models import Unit, UnitType, Modality

import re

#----------------------------------------------------------------------
def create_user(is_staff=False,is_superuser=False):
    """"""
    u = User(username="testuser",is_staff=is_staff,is_superuser=is_superuser)
    u.save()
    return u

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
            f = models.Frequency(
                name=t,slug=s,
                nominal_interval=nom, due_interval=due, overdue_interval=overdue
            )
            f.save()
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
            f = models.Frequency(
                name=t,slug=s,
                nominal_interval=nom, due_interval=due, overdue_interval=overdue
            )
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



#============================================================================
class TestRefTols(TestCase):
    """make sure references/tolerance and pass/fail are operating correctly"""

    #----------------------------------------------------------------------
    def test_bool(self):
        test = models.Test(type=models.BOOLEAN)
        self.yes_ref = models.Reference(type = models.BOOLEAN,value = True,)
        self.no_ref = models.Reference(type = models.BOOLEAN,value = False,)

        yes_instance = models.TestInstance(value=1,test=test)
        no_instance = models.TestInstance(value=0,test=test)

        ok_tests = (
            (yes_instance,self.yes_ref),
            (no_instance,self.no_ref),
        )
        action_tests = (
            (no_instance,self.yes_ref),
            (yes_instance,self.no_ref),
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
    def test_absolute(self):

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
    def test_percent(self):

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
    def test_percent_diff_for_zero_ref(self):
        """A percent difference for a zero reference value doesn't make any sense
        Creating a UnitTestInfo object with a percent reference and zero value
        should fail.  Likewise, trying to calculate a percent difference for a
        zero based reference should raise a ValueError
        """

        ti = models.TestInstance(test=models.Test(type=models.SIMPLE))
        ti.tolerance = models.Tolerance(type=models.PERCENT,)
        ti.reference = models.Reference(type=models.NUMERICAL,value=0)
        self.assertRaises(ValueError,ti.calculate_pass_fail)


    #----------------------------------------------------------------------
    def test_skipped(self):
        tol = models.Tolerance(type=models.PERCENT,)
        ti = models.TestInstance(skipped=True)
        ti.calculate_pass_fail()
        self.assertEqual(models.NOT_DONE,ti.pass_fail)

#============================================================================
class BaseQATestCase(TestCase):

    fixtures = [
        "test/units",
        "test/categories",
        "test/references",
        "test/tolerances",
        "test/users",
    ]

    #----------------------------------------------------------------------
    def setUp(self):
        self.cat = models.Category.objects.get(pk=1)

        self.unit = Unit.objects.get(pk=1)
        self.user = User.objects.get(pk=1)

        self.test = models.Test(
            name = "name",
            slug="name",
            description = "desc",
            type = models.SIMPLE,
            category = self.cat,
            created_by = self.user,
            modified_by = self.user,
        )
        self.test.save()

        self.test2 = models.Test(
            name = "name2",
            slug="name2",
            description = "desc2",
            type = models.SIMPLE,
            category = self.cat,
            created_by = self.user,
            modified_by = self.user,
        )
        self.test2.save()


        self.test_list = models.TestList(
            name = "test list",
            slug = "test-list",
            description = "foo",
            created_by = self.user,
            modified_by = self.user,
        )
        self.test_list.save()

        self.test_list_membership = models.TestListMembership(
            test_list = self.test_list,
            test= self.test,
            order = 0
        )
        self.test_list_membership.save()

        self.ref = models.Reference.objects.get(pk=1)
        self.tol = models.Tolerance.objects.get(pk=1)

        self.daily = models.Frequency(
            name="Daily",
            slug="daily",
            nominal_interval=1,
            due_interval=1,
            overdue_interval=1,
        )
        self.daily.save()

        self.unit_test_assign = models.UnitTestInfo(
            unit = self.unit,
            test = self.test,
            reference = self.ref,
            tolerance = self.tol,
            frequency = self.daily
        )
        self.unit_test_assign.save()

        self.unit_test_list_assign = models.UnitTestCollection(
            unit = self.unit,
            object_id = self.test_list.pk,
            content_type = ContentType.objects.get(app_label="qa", model="testlist"),
            frequency = self.daily
        )
        self.unit_test_list_assign.save()

        self.unreviewed = models.TestInstanceStatus(
            name="Unreviewed",
            slug="unreviewed",
            is_default=True,
            requires_review=True
        )
        self.unreviewed.save()


#============================================================================
class TestTests(BaseQATestCase):

    #----------------------------------------------------------------------
    def test_is_boolean(self):
        self.test.type = models.BOOLEAN
        self.ref.value = 0
        self.ref.save()
        self.test.save()
        self.assertTrue(self.test.is_boolean())

    #----------------------------------------------------------------------
    def test_set_references_links(self):

        set_ref_link = self.test.set_references()
        self.client.login(username="testuser",password="password")

        for url in re.findall('href="(.*?)"',set_ref_link):
            response = self.client.get(url)
            self.assertEqual(response.status_code,200)

    #----------------------------------------------------------------------
    def test_unit_ref_tol(self):
        t = self.unit_test_assign.tolerance
        r = self.unit_test_assign.reference

        ref_tols = (
            (r,t,[t.act_low,t.tol_low,r.value,t.tol_high,t.act_high]),
            (r,None,[None, None,r.value, None, None]),
            (None, None, [None, None,None, None, None]),
            (None,t,[t.act_low,t.tol_low,None,t.tol_high,t.act_high]),
        )

        for ref, tol, result in ref_tols:

            self.unit_test_assign.tolerance = tol
            self.unit_test_assign.reference = ref
            self.unit_test_assign.save()

            self.assertListEqual(
                self.test.ref_tol_for_unit(self.unit),
                result,
            )
    #----------------------------------------------------------------------
    def test_invalid_calc_procedure(self):

        test = models.Test(type=models.SIMPLE)

        #don't need to check if not composite
        self.assertIsNone(test.clean_calculation_procedure())

        #calc procedure but test type not compsite
        test.calculation_procedure = "foo"
        self.assertRaises(ValidationError, test.clean_calculation_procedure)

        test.type = models.COMPOSITE

        #no result line defined
        self.assertRaises(ValidationError, test.clean_calculation_procedure)

        invalid_calc_procedures = (
            "resul t = a + b",
            "_result = a + b",
            "0result = a+b",
            " result = a + b",
            "result_=foo",
            "",
            "foo = a +b",
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
        test = models.Test(type=models.COMPOSITE)

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
    def test_constant_val(self):
        test = models.Test(type=models.SIMPLE)
        test.constant_value = 1
        self.assertRaises(ValidationError,test.clean_constant_value)

        test.constant_value = None
        test.type = models.CONSTANT
        self.assertRaises(ValidationError,test.clean_constant_value)

    #----------------------------------------------------------------------
    def test_slug(self):

        invalid = ( "0 foo", "foo ", " foo" "foo bar", "foo*bar", "%foo", "foo$" )

        for i in invalid:
            self.test.slug = i
            try:
                msg = "Short name should have failed but passed: %s" % i
                self.test.clean_slug()
            except ValidationError:
                msg = ""

            self.assertTrue(len(msg)==0, msg=msg)

        valid = ("foo", "f6oo", "foo6","_foo","foo_","foo_bar",)
        for v in valid:
            self.test.slug = v
            try:
                msg = ""
                self.test.clean_slug()
            except ValidationError:
                msg = "Short name should have passed but failed: %s" % v
            self.assertTrue(len(msg)==0, msg=msg)
    #----------------------------------------------------------------------
    def test_clean_fields(self):
        self.test.clean_fields()

    #----------------------------------------------------------------------
    def test_history(self):
        td = timezone.timedelta
        now = timezone.now()


        #values purposely created out of order to make sure history
        #returns in correct order (i.e. ordered by date)
        history = [
            (now+td(days=4), 5., models.NO_TOL, self.unreviewed),
            (now+td(days=1), 5., models.NO_TOL, self.unreviewed),
            (now+td(days=3), 6., models.NO_TOL, self.unreviewed),
            (now+td(days=2), 7., models.NO_TOL, self.unreviewed),
        ]
        for wc, val, _, _ in history:
            ti1 = models.TestInstance(
                test=self.test,
                value=val,
                unit=self.unit,
                created_by=self.test.created_by,
                modified_by=self.test.created_by,
                work_completed = wc,
                status=self.unreviewed
            )
            ti1.save()

        db_hist = self.test.history_for_unit(self.unit)

        sorted_hist = list(sorted(history))

        self.assertListEqual(sorted_hist,db_hist)

        #test works correctly for just unit num
        db_hist = self.test.history_for_unit(self.unit.number)
        self.assertListEqual(sorted_hist,db_hist)

        #test returns correct number of results
        db_hist = self.test.history_for_unit(self.unit.number,number=2)
        self.assertListEqual(sorted_hist[-2:],db_hist)


#============================================================================
class TestUnitTestInfo(BaseQATestCase):

    #----------------------------------------------------------------------
    def test_duplicate(self):

        dup  = models.UnitTestInfo(
            unit = self.unit,
            test = self.test,
            frequency = self.unit_test_assign.frequency,
            reference = self.ref,
            tolerance = self.tol,
        )

        self.assertRaises(IntegrityError,dup.save)
    #----------------------------------------------------------------------
    def test_invalid_bools(self):

        self.test.type = models.BOOLEAN
        self.ref.value = -1
        self.ref.save()
        self.assertRaises(ValidationError,self.unit_test_assign.clean)

        self.assertRaises(ValidationError,self.test.save)

    #----------------------------------------------------------------------
    def test_invalid_percent(self):
        self.tol.type = models.PERCENT
        self.ref.value = 0
        self.ref.save()
        self.assertRaises(ValidationError,self.unit_test_assign.clean)

    #----------------------------------------------------------------------
    def test_boolean_tolerance(self):
        #tolerance should be left blank if test is boolean
        self.test.type = models.BOOLEAN
        self.ref.value = 0.
        self.ref.save()
        self.test.save()

        self.assertRaisesRegexp(ValidationError,"leave tolerance blank",self.unit_test_assign.full_clean)

#============================================================================
class TestTestList(BaseQATestCase):

    #----------------------------------------------------------------------
    def test_last_completed(self):

        td = timezone.timedelta
        now = timezone.now()
        last_completed_date = now+td(days=3)

        self.assertIsNone(self.unit_test_list_assign.last_completed_instance())

        #values purposely created out of order to make sure correct
        #last completed instance is returned correctly
        history = [
            (now+td(days=1), 5, models.NO_TOL, self.unreviewed),
            (last_completed_date, 6, models.NO_TOL, self.unreviewed),
            (now+td(days=2), 7, models.NO_TOL, self.unreviewed),
        ]
        for wc, val, _, _ in history:
            tli = models.TestListInstance(
                test_list=self.test_list,
                unit=self.unit,
                created_by=self.test.created_by,
                modified_by=self.test.created_by,
            )
            tli.work_completed = wc

            tli.save()
            ti1 = models.TestInstance(
                test=self.test,
                value=val,
                unit=self.unit,
                test_list_instance = tli,
                created_by=self.test.created_by,
                modified_by=self.test.created_by,
                work_completed = wc,
                status=self.unreviewed
            )
            ti1.save()

        last = self.unit_test_list_assign.last_completed_instance()

        unreviewed = self.unit_test_list_assign.unreviewed_instances()
        self.assertEqual(set(unreviewed), set(models.TestListInstance.objects.all()))

        unreviewed_tests = self.unit_test_list_assign.unreviewed_test_instances()
        self.assertEqual(set(unreviewed_tests), set(models.TestInstance.objects.all()))

        self.assertEqual(last.work_completed,last_completed_date)

        self.assertEqual(list(self.unit_test_list_assign.history()),list(models.TestListInstance.objects.all()))
    #----------------------------------------------------------------------
    def test_sublist(self):
        sub_test = models.Test(
            name = "sub",
            slug="sub",
            description = "desc",
            type = models.SIMPLE,
            category = self.cat,
            created_by = self.user,
            modified_by = self.user,
        )
        sub_test.save()

        sub_list = models.TestList(
            name = "sub test list",
            slug = "sub test-list",
            description = "foo",
            created_by = self.user,
            modified_by = self.user,
        )
        sub_list.save()

        sub_test_list_membership = models.TestListMembership(
            test_list = sub_list,
            test= sub_test,
            order = 0
        )
        sub_test_list_membership.save()


        self.test_list.sublists.add(sub_list)
        self.test_list.save()
        self.assertListEqual([self.test,sub_test],list(self.test_list.all_tests()))
        self.assertListEqual([self.test,sub_test],list(self.test_list.ordered_tests()))

        self.assertEqual(1, models.UnitTestInfo.objects.filter( test = sub_test).count())

        sub_test2 = models.Test(
            name = "sub2",
            slug="sub2",
            description = "desc",
            type = models.SIMPLE,
            category = self.cat,
            created_by = self.user,
            modified_by = self.user,
        )
        sub_test2.save()

        sub_test_list_membership2 = models.TestListMembership(
            test_list = sub_list,
            test= sub_test2,
            order = 0
        )
        sub_test_list_membership2.save()

        self.assertEqual(1, models.UnitTestInfo.objects.filter( test = sub_test2).count())


    #----------------------------------------------------------------------
    def test_set_references(self):

        set_ref_link = self.test_list.set_references()
        self.client.login(username="testuser",password="password")
        import re
        urls = re.findall('href="(.*?)"',set_ref_link)
        self.assertEqual(len(urls),1)
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code,200)

        self.unit_test_list_assign.delete()

        unassigned = "<em>Currently not assigned to any units</em>"
        self.assertEqual(unassigned,self.test_list.set_references())
    #----------------------------------------------------------------------
    def test_manage(self):
        utls = models.UnitTestCollection.objects.by_unit(self.unit).all()
        self.unit_test_list_assign.delete()
        assignments = []
        for freq in models.Frequency.objects.all():
            unit_test_list_assign = models.UnitTestCollection(
                unit = self.unit,
                object_id = self.test_list.pk,
                content_type = ContentType.objects.get(app_label="qa", model="testlist"),
                frequency = freq
            )
            unit_test_list_assign.save()
            assignments.append(unit_test_list_assign)

        utls = models.UnitTestCollection.objects.by_unit(self.unit).all()
        #freqs = utls.values_list("frequency",flat=True)
        #self.assertSetEqual(set(freqs),set([x[0] for x in models.Frequency.objects.frequency_choices()]))

        utls = models.UnitTestCollection.objects.by_frequency(self.daily)
        self.assertEqual(utls.count(),1)

        utls = models.UnitTestCollection.objects.by_unit_frequency(self.unit,self.daily)
        self.assertEqual(utls.count(),1)

        self.assertEqual(
            list(models.UnitTestCollection.objects.test_lists().all()),
            assignments
        )
    #----------------------------------------------------------------------
    def test_get_list_functions(self):

        self.assertEqual(self.test_list,self.test_list.get_list())
        self.assertEqual(self.test_list,self.test_list.next_list(None))
        self.assertEqual(self.test_list,self.test_list.first())

    #----------------------------------------------------------------------
    def test_next_for_unit(self):
        self.assertEqual(self.test_list,self.unit_test_list_assign.next_list())

    #----------------------------------------------------------------------
    def test_due_date(self):
        now = timezone.now()
        ti = models.TestInstance(
            test=self.test,
            unit=self.unit,
            created_by=self.test.created_by,
            modified_by=self.test.created_by,
            status=self.unreviewed
        )
        ti.work_completed = now
        ti.save()


        due = self.unit_test_list_assign.due_date()
        self.assertEqual(due,ti.work_completed+self.daily.nominal_delta())


        tlm = models.TestListMembership(test_list=self.test_list,test=self.test2,order=1)
        tlm.save()

        due = self.unit_test_list_assign.due_date()
        self.assertEqual(due,ti.work_completed+self.daily.nominal_delta())

        ti2 = models.TestInstance(
            test=self.test2,
            unit=self.unit,
            created_by=self.test.created_by,
            modified_by=self.test.created_by,
            status=self.unreviewed
        )
        ti2.work_completed = now-timezone.timedelta(days=3)
        ti2.save()
        due = self.unit_test_list_assign.due_date()
        self.assertEqual(due,now-timezone.timedelta(days=2))
    #----------------------------------------------------------------------
    def test_name(self):
        self.assertEqual(str(self.unit_test_list_assign),self.unit_test_list_assign.name())
    #----------------------------------------------------------------------
    def test_pass_fail(self):
        """"""

        tests = []
        utls = []
        utis = []

        ref = models.Reference(type=models.NUMERICAL,value=100.)
        tol = models.Tolerance(
            type=models.PERCENT,
            act_low = -3,
            tol_low = -2,
            tol_high=  2,
            act_high=  3,
        )
        self.test.delete()
        self.test_list_membership.delete()

        for i in range(6):
            test = models.Test(
                name = "name2",
                slug="name2",
                description = "desc2",
                type = models.SIMPLE,
                category = self.cat,
                created_by = self.user,
                modified_by = self.user,
            )
            test.save()
            tests.append(test)

            m = models.TestListMembership(
                test_list = self.test_list,
                test = test,
                order = i
            )
            m.save()



        now = timezone.now()
        tli = models.TestListInstance(
            test_list=self.test_list,
            unit=self.unit,
            created_by=tests[0].created_by,
            modified_by=tests[0].created_by,
            work_completed = now
        )
        tli.save()
        self.assertEqual(tli.work_completed,self.unit_test_list_assign.last_done_date())

        values = [None, None,96,97,100,100]

        tis = []
        for i,(v,test) in enumerate(zip(values,tests)):
            ti = models.TestInstance(
                test=test,
                value=v,
                unit=self.unit,
                test_list_instance = tli,
                created_by=test.created_by,
                modified_by=test.created_by,
                work_completed = now,
                tolerance=tol,
                reference=ref,
                status = self.unreviewed
            )
            if i == 0:
                ti.skipped = True
            elif i == 1:
                ti.tolerance = None
                ti.reference = None

            ti.save()

        pf_status = tli.pass_fail_status()
        for pass_fail, _, tests in pf_status:

            if pass_fail == models.OK:
                self.assertTrue(len(tests)==2)
            else:
                self.assertTrue(len(tests)==1)

        formatted = "1 Not Done, 2 OK, 1 Tolerance, 1 Action, 1 No Tol Set"
        self.assertEqual(tli.pass_fail_status(True),formatted)

        statuses = tli.status()

    #----------------------------------------------------------------------
    def test_content_type(self):
        self.assertEqual(ContentType.objects.get_for_model(models.TestList),self.test_list.content_type())


#============================================================================
class CycleTest(BaseQATestCase):
    NLISTS = 2
    #----------------------------------------------------------------------
    def setUp(self):
        super(CycleTest,self).setUp()
        test_lists = []
        for i,test in zip(range(1,self.NLISTS+1),[self.test,self.test2]):
            test_list = models.TestList(
                name="test %d"%i,
                slug="test %d"%i,
                description="blah",
                created_by = self.user,
                modified_by = self.user,
            )
            test_list.save()
            test_lists.append(test_list)
            membership = models.TestListMembership(
                test_list=test_list,
                test=test, order=0
            )
            membership.save()
            test_list.save()

        self.cycle = models.TestListCycle(name="test cycle")
        self.cycle.created_by = self.user
        self.cycle.modified_by = self.user
        self.cycle.save()
        self.cycle.units = Unit.objects.all()
        self.cycle.save()

        for order,tl in enumerate(test_lists):

            membership = models.TestListCycleMembership(
                test_list = tl,
                order = order,
                cycle = self.cycle
            )
            membership.save()
            if order == 0:
                self.first_membership = membership

        self.unit_test_list_assign = models.UnitTestCollection(
            unit = self.unit,
            object_id = self.cycle.pk,
            content_type = ContentType.objects.get(app_label="qa", model="testlistcycle"),
            frequency = self.daily
        )

    #----------------------------------------------------------------------
    def get_instance_for_list(self,test_list,unit):
        """"""
        instance = models.TestListInstance(
            test_list=test_list,
            unit=unit,
            created_by=self.user,
            modified_by=self.user
        )
        instance.save()

        for test in test_list.tests.all():
            test_instance = models.TestInstance(
                test=test,
                unit=unit,
                value=1.,
                skipped=False,
                test_list_instance=instance,
                reference = models.Reference.objects.get(pk=1),
                tolerance = models.Tolerance.objects.get(pk=1),
                status=self.unreviewed,
                created_by=self.user,
                modified_by=self.user
            )
            test_instance.save()

        instance.save()
        return instance
    #----------------------------------------------------------------------
    def test_never_performed(self):
        unit = self.cycle.units.all()[0]
        self.assertIsNone(self.unit_test_list_assign.last_completed_instance())

    #----------------------------------------------------------------------
    def test_last_instance_for_unit(self):

        unit = self.cycle.units.all()[0]
        test_list = self.cycle.first()
        instance = self.get_instance_for_list(test_list,unit)
        self.assertEqual(instance,self.unit_test_list_assign.last_completed_instance())
    #----------------------------------------------------------------------
    def test_history(self):
        i1 = self.get_instance_for_list(self.cycle.first(),self.unit)
        i2 = self.get_instance_for_list(self.cycle.next_list(i1.test_list),self.unit)
        self.assertEqual(list(self.unit_test_list_assign.history()),[i1,i2])
    #----------------------------------------------------------------------
    def test_next_for_unit(self):

        unit = self.cycle.units.all()[0]

        #perform a full cycle ensuring a wrap
        nlist = self.cycle.test_lists.count()
        memberships = models.TestListCycleMembership.objects.filter(
            cycle=self.cycle
        ).order_by("order")

        for i, expected in enumerate(memberships):

            #get next to perform (on first cycle through we should get first list)
            next_ = self.unit_test_list_assign.next_list()
            self.assertEqual(next_, expected.test_list)

            #now perform the test list
            self.get_instance_for_list(next_,unit)

        #confirm that we have wrapped around to the beginning again
        next_ =  self.unit_test_list_assign.next_list()
        self.assertEqual(next_,memberships[0].test_list)


    #----------------------------------------------------------------------
    def test_length(self):
        self.assertEqual(self.NLISTS,len(self.cycle))
        self.assertEqual(0,len(models.TestListCycle()))
    #----------------------------------------------------------------------
    def test_first(self):
        self.assertEqual(self.cycle.first(),self.first_membership.test_list)
        self.assertEqual(None,models.TestListCycle().first())
    #----------------------------------------------------------------------
    def test_membership_by_order(self):
        self.assertEqual(self.cycle.membership_by_order(0),self.first_membership)
        self.assertEqual(None,self.cycle.membership_by_order(100))
    #----------------------------------------------------------------------
    def test_all_tests(self):
        self.assertEqual([self.test,self.test2],list(self.cycle.all_tests()))
    #----------------------------------------------------------------------
    def test_next_list(self):
        tl1 = self.cycle.test_lists.all()[0]
        tl2 = self.cycle.test_lists.all()[1]
        self.assertEqual(tl1,self.cycle.next_list(tl2))
        self.assertEqual(tl2,self.cycle.next_list(tl1))
        self.assertEqual(self.cycle.first(),self.cycle.next_list(None))
    #----------------------------------------------------------------------
    def test_get_list(self):
        tl1 = self.cycle.test_lists.all()[0]
        tl2 = self.cycle.test_lists.all()[1]
        self.assertEqual(tl1,self.cycle.get_list(0))
        self.assertEqual(tl2,self.cycle.get_list(1))
        self.assertEqual(None,self.cycle.get_list(2))


    #----------------------------------------------------------------------
    def test_due_date(self):
        now = timezone.now()
        ti = models.TestInstance(
            test=self.test,
            unit=self.unit,
            created_by=self.test.created_by,
            modified_by=self.test.created_by,
            status=self.unreviewed
        )
        ti.work_completed = now
        ti.save()


        due = self.unit_test_list_assign.due_date()
        self.assertEqual(due,ti.work_completed+self.daily.nominal_delta())


        tlm = models.TestListMembership(test_list=self.test_list,test=self.test2,order=1)
        tlm.save()

        due = self.unit_test_list_assign.due_date()
        self.assertEqual(due,ti.work_completed+self.daily.nominal_delta())

        ti2 = models.TestInstance(
            test=self.test2,
            unit=self.unit,
            created_by=self.test.created_by,
            modified_by=self.test.created_by,
            status=self.unreviewed
        )
        ti2.work_completed = now+timezone.timedelta(days=3)
        ti2.save()

        due = self.unit_test_list_assign.due_date()
        self.assertEqual(due,now+timezone.timedelta(days=4))

    #----------------------------------------------------------------------
    def test_content_type(self):
        self.assertEqual(ContentType.objects.get_for_model(models.TestListCycle),self.cycle.content_type())


if __name__ == "__main__":
    setup_test_environment()
    unittest.main()