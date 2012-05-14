from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import setup_test_environment
from django.utils import unittest

from django.contrib.auth.models import User
from qatrack.qa import models
from qatrack.units.models import Unit



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




if __name__ == "__main__":
    setup_test_environment()
    unittest.main()