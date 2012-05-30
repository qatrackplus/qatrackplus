from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import Client
from django.test.utils import setup_test_environment
from django.utils import unittest

from django.contrib.auth.models import User
from qatrack.qa import models
from qatrack.units.models import Unit

def create_basic_test(name,test_type=models.SIMPLE):

    cat = models.Category.objects.get(pk=1)

    unit = Unit.objects.get(pk=1)
    user = User.objects.get(pk=1)
    test = models.Test(
        name = name,
        short_name=name,
        description = "foo",
        type = test_type,
        category = cat,
        created_by = user,
        modified_by = user,
    )

    test.save()

    test_list = models.TestList(
        name="test list for %s" % name,
        slug="test list%s" % name,
        description="blah",
        active=True,
        created_by = user,
        modified_by = user,
    )
    test_list.save()

    membership = models.TestListMembership(test_list=test_list, test=test, order=1)
    membership.save()
    test_list.save()

    #get daily task list for unit
    utl = models.UnitTestLists.objects.get(
        unit = unit,
        frequency = models.DAILY,
    )

    utl.test_lists.add(test_list)
    utl.save()

    unit_test_info = models.UnitTestInfo.objects.get(
        unit=unit,
        test = test
    )

    return test, test_list, utl, unit_test_info

#============================================================================
class CycleTest(TestCase):
    """Test cases for cycles"""
    fixtures = [
        "test/units",
        "test/categories",
        "test/references",
        "test/tolerances",
        "test/users",
    ]
    NLISTS = 2
    #----------------------------------------------------------------------
    def setUp(self):

        self.user = User.objects.get(pk=1)
        cat = models.Category.objects.get(pk=1)

        test = models.Test(
            name = "test",
            short_name="test",
            description = "desc",
            type = models.SIMPLE,
            category = cat,
            created_by = self.user,
            modified_by = self.user,
        )

        test.save()

        for i in range(1,self.NLISTS+1):
            test_list = models.TestList(
                name="test %d"%i,
                slug="test %d"%i,
                description="blah",
                active=True,
                created_by = self.user,
                modified_by = self.user,
            )
            test_list.save()
            membership = models.TestListMembership(test_list=test_list,
                                test=test, order=1)
            membership.save()
            test_list.save()

        self.cycle = models.TestListCycle(name="test cycle")
        self.cycle.save()
        self.cycle.units = Unit.objects.all()
        self.cycle.save()
        test_lists = models.TestList.objects.all()

        for order,tl in enumerate(test_lists):
            membership = models.TestListCycleMembership(
                test_list = tl,
                order = order,
                cycle = self.cycle
            )
            membership.save()

    #----------------------------------------------------------------------
    def get_instance_for_test_list(self,test_list,unit):
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
                status=models.UNREVIEWED,
                created_by=self.user,
                modified_by=self.user
            )
            test_instance.save()

        instance.save()
        return instance
    #----------------------------------------------------------------------
    def test_never_performed(self):
        unit = self.cycle.units.all()[0]
        self.assertIsNone(self.cycle.last_completed(unit))

    #----------------------------------------------------------------------
    def test_last_for_unit(self):

        unit = self.cycle.units.all()[0]
        test_list = self.cycle.first().test_list
        instance = self.get_instance_for_test_list(test_list,unit)
        membership = models.TestListCycleMembership.objects.get(
            cycle=self.cycle,order=0
        )
        self.assertEqual(membership,self.cycle.last_completed(unit))
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
            next_ = self.cycle.next_for_unit(unit)
            self.assertEqual(next_, expected)

            #now perform the test list
            self.get_instance_for_test_list(next_.test_list,unit)

        #confirm that we have wrapped around to the beginning again
        next_ =  self.cycle.next_for_unit(unit)
        self.assertEqual(next_,memberships[0])

    #----------------------------------------------------------------------
    def test_length(self):
        self.assertEqual(self.NLISTS,len(self.cycle))


class UnitTestListTests(TestCase):

    fixtures = [
        "test/units",
        "test/categories",
        "test/references",
        "test/tolerances",
        "test/users",
    ]
    NLISTS = 2
    #----------------------------------------------------------------------
    def setUp(self):

        self.user = User.objects.get(pk=1)
        cat = models.Category.objects.get(pk=1)
        self.unit = Unit.objects.get(pk=1)

        self.test1 = models.Test(
            name = "test1",
            short_name="test1",
            description = "desc",
            type = models.SIMPLE,
            category = cat,
            created_by = self.user,
            modified_by = self.user,
        )

        self.test1.save()


        self.test2 = models.Test(
            name = "test2",
            short_name="test2",
            description = "desc",
            type = models.SIMPLE,
            category = cat,
            created_by = self.user,
            modified_by = self.user,
        )
        self.test2.save()

        self.test_list = models.TestList(
            name="test list",
            slug="test list",
            description="blah",
            active=True,
            created_by = self.user,
            modified_by = self.user,
        )
        self.test_list.save()
        membership = models.TestListMembership(test_list=self.test_list, test=self.test1, order=1)
        membership.save()
        self.test_list.save()

        #get daily task list for unit
        self.utl = models.UnitTestLists.objects.get(
            unit = self.unit,
            frequency = models.DAILY,
        )

        self.utl.save()
        self.utl.test_lists.add(self.test_list)
        self.utl.save()
    #----------------------------------------------------------------------
    def test_first_added(self):
        """"""
        unit_test_info = models.UnitTestInfo.objects.get(
            unit=self.unit,
            test = self.test1
        )
    #----------------------------------------------------------------------
    def test_add_to_existing(self):
        """"""
        membership = models.TestListMembership(
            test_list=self.test_list,
            test=self.test2,
            order=2
        )
        membership.save()
        self.test_list.save()

        unit_test_info = models.UnitTestInfo.objects.get(
            unit=self.unit,
            test = self.test2
        )


#============================================================================
class RefTolTests(TestCase):
    """make sure references/tolerance and pass/fail are operating correctly"""

    fixtures = [
        "test/units",
        "test/categories",
        "test/users",
    ]

    #----------------------------------------------------------------------
    def test_bool(self):
        test = models.Test(type=models.BOOLEAN)
        self.yes_ref = models.Reference(type = models.BOOLEAN,value = True,)
        self.no_ref = models.Reference(type = models.BOOLEAN,value = False,)

        self.bool_tol = models.Tolerance(
            type = models.ABSOLUTE,
            act_low =1E-10, tol_low =1E-10,
            tol_high=1E-10, act_high=1E-10,
        )

        yes_instance = models.TestInstance(value=1,test=test)
        no_instance = models.TestInstance(value=0,test=test)

        ok_tests = (
            self.bool_tol.test_instance(yes_instance,self.yes_ref),
            self.bool_tol.test_instance(no_instance,self.no_ref),
        )
        action_tests = (
            self.bool_tol.test_instance(no_instance,self.yes_ref),
            self.bool_tol.test_instance(yes_instance,self.no_ref),
        )
        for test in ok_tests:
            self.assertEqual(models.OK,test)
        for test in action_tests:
            self.assertEqual(models.ACTION,test)
    #----------------------------------------------------------------------
    def test_absolute(self):

        test = models.Test(type=models.SIMPLE)
        ti = models.TestInstance(test=test)
        ref = models.Reference(type=models.NUMERICAL,value=100.)
        tol = models.Tolerance(
            type=models.ABSOLUTE,
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
            r = tol.test_instance(ti,ref)
            self.assertEqual(result,r)

    #----------------------------------------------------------------------
    def test_percent(self):

        test = models.Test(type=models.SIMPLE)
        ti = models.TestInstance(test=test)
        ref = models.Reference(type=models.NUMERICAL,value=100.)
        tol = models.Tolerance(
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
            r = tol.test_instance(ti,ref)
            self.assertEqual(result,r)

    #----------------------------------------------------------------------
    def test_percent_diff_for_zero_ref(self):
        """A percent difference for a zero reference value doesn't make any sense
        Creating a UnitTestInfo object with a percent reference and zero value
        should fail.  Likewise, trying to calculate a percent difference for a
        zero based reference should raise a ValueError
        """

        tol = models.Tolerance(type=models.PERCENT,)
        with self.assertRaises(ValueError):
            tol.test_instance(
                models.TestInstance(test=models.Test(type=models.SIMPLE)),
                models.Reference(type=models.NUMERICAL,value=0)
            )

    #----------------------------------------------------------------------
    def test_create_unittestinfo_invalid(self):


        cat = models.Category.objects.get(pk=1)
        unit = Unit.objects.get(pk=1)
        user = User.objects.get(pk=1)
        test1 = models.Test(
            name = "test1",
            short_name="test1",
            description = "desc",
            type = models.SIMPLE,
            category = cat,
            created_by = user,
            modified_by = user,
        )

        test1.save()

        test_list = models.TestList(
            name="test list",
            slug="test list",
            description="blah",
            active=True,
            created_by = user,
            modified_by = user,
        )
        test_list.save()

        membership = models.TestListMembership(test_list=test_list, test=test1, order=1)
        membership.save()
        test_list.save()

        #get daily task list for unit
        utl = models.UnitTestLists.objects.get(unit = unit, frequency = models.DAILY,)
        utl.test_lists.add(test_list)
        utl.save()

        unit_test_info = models.UnitTestInfo.objects.get(
            unit=unit,
            test = test1
        )
        unit_test_info.reference = models.Reference(type=models.NUMERICAL,value=0)
        unit_test_info.tolerance = models.Tolerance(type=models.PERCENT)

        with self.assertRaises(ValidationError):
            unit_test_info.clean()



#============================================================================
class TestTests(TestCase):
    fixtures = [
        "test/units",
        "test/categories",
        "test/references",
        "test/tolerances",
        "test/users",
    ]

    #----------------------------------------------------------------------
    def test_is_boolean(self):
        test = models.Test(type=models.BOOLEAN)
        self.assertTrue(test.is_boolean())

    #----------------------------------------------------------------------
    def test_set_references(self):
        test,test_list,utl, unit_test_info = create_basic_test("test")
        set_ref_link = test.set_references()
        self.client.login(username="testuser",password="password")
        import re
        for url in re.findall('href="(.*?)"',set_ref_link):
            response = self.client.get(url)
            self.assertEqual(response.status_code,200)

    #----------------------------------------------------------------------
    def test_unit_ref_tol(self):
        """"""
        test,test_list,utl, unit_test_info = create_basic_test("test")
        r = models.Reference.objects.get(pk=1)
        t = models.Tolerance.objects.get(pk=1)

        unit_test_info.reference = r
        unit_test_info.tolerance = t

        unit_test_info.save()
        self.assertListEqual(
            test.unit_ref_tol(utl.unit),
            [t.act_low,t.tol_low,r.value,t.tol_high,t.act_high]
        )

        unit_test_info.tolerance = None
        unit_test_info.save()
        self.assertListEqual(
            test.unit_ref_tol(utl.unit),
            [None, None,r.value, None, None]
        )

        unit_test_info.reference = None
        unit_test_info.save()
        self.assertListEqual(
            test.unit_ref_tol(utl.unit),
            [None, None,None, None, None]
        )

        unit_test_info.tolerance = t
        unit_test_info.save()
        self.assertListEqual(
            test.unit_ref_tol(utl.unit),
            [t.act_low,t.tol_low,None,t.tol_high,t.act_high]
        )

    #----------------------------------------------------------------------
    def test_invalid_calc_procedure(self):

        test = models.Test(type=models.SIMPLE)

        #don't need to check if not composite
        self.assertIsNone(test.clean_calculation_procedure())

        #calc procedure but test type not compsite
        test.calculation_procedure = "foo"
        with self.assertRaises(ValidationError):
            test.clean_calculation_procedure()

        test.type = models.COMPOSITE

        #no result line defined
        with self.assertRaises(ValidationError):
            test.clean_calculation_procedure()

        invalid_calc_procedures = (
            "resul t = a + b",
            "_result = a + b",
            "0result = a+b",
            " result = a + b",
            "result_=foo",
        )

        for icp in invalid_calc_procedures:
            test.calculation_procedure = icp
            try:
                msg = ""
                test.clean_calculation_procedure()
            except ValidationError:
                msg = icp
            self.assertTrue(len(msg)>0,msg)

    #----------------------------------------------------------------------
    def test_valid_calc_procedure(self):
        test = models.Test(type=models.SIMPLE)
        test.type = models.COMPOSITE

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
                test.clean_calculation_procedure()
            except:
                print vcp
                raise


if __name__ == "__main__":
    setup_test_environment()
    unittest.main()