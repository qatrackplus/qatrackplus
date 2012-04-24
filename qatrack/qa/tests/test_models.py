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

        tli = models.TaskListItem(
            name = "test",
            short_name="test",
            description = "desc",
            task_type = models.SIMPLE,
            category = cat,
            created_by = self.user,
            modified_by = self.user,
        )

        tli.save()

        for i in range(1,self.NLISTS+1):
            task_list = models.TaskList(
                name="test %d"%i,
                slug="test %d"%i,
                description="blah",
                active=True,
                created_by = self.user,
                modified_by = self.user,
            )
            task_list.save()
            membership = models.TaskListMembership(task_list=task_list,
                                task_list_item=tli, order=1)
            membership.save()
            # task_list.task_list_items.add(tli)
            task_list.save()

        self.cycle = models.TaskListCycle(name="test cycle")
        self.cycle.save()
        self.cycle.units = Unit.objects.all()
        self.cycle.save()
        task_lists = models.TaskList.objects.all()

        for order,tl in enumerate(task_lists):
            membership = models.TaskListCycleMembership(
                task_list = tl,
                order = order,
                cycle = self.cycle
            )
            membership.save()

    #----------------------------------------------------------------------
    def get_instance_for_task_list(self,task_list,unit):
        """"""
        instance = models.TaskListInstance(
            task_list=task_list,
            unit=unit,
            created_by=self.user,
            modified_by=self.user
        )
        instance.save()

        for item in task_list.task_list_items.all():
            item_instance = models.TaskListItemInstance(
                task_list_item=item,
                unit=unit,
                value=1.,
                skipped=False,
                task_list_instance=instance,
                reference = models.Reference.objects.get(pk=1),
                tolerance = models.Tolerance.objects.get(pk=1),
                status=models.UNREVIEWED,
                created_by=self.user,
                modified_by=self.user
            )
            item_instance.save()

        instance.save()
        return instance
    #----------------------------------------------------------------------
    def test_never_performed(self):
        unit = self.cycle.units.all()[0]
        self.assertIsNone(self.cycle.last_completed(unit))

    #----------------------------------------------------------------------
    def test_last_for_unit(self):

        unit = self.cycle.units.all()[0]
        task_list = self.cycle.first().task_list
        instance = self.get_instance_for_task_list(task_list,unit)
        membership = models.TaskListCycleMembership.objects.get(
            cycle=self.cycle,order=0
        )
        self.assertEqual(membership,self.cycle.last_completed(unit))
    #----------------------------------------------------------------------
    def test_next_for_unit(self):

        unit = self.cycle.units.all()[0]

        #perform a full cycle ensuring a wrap
        nlist = self.cycle.task_lists.count()
        memberships = models.TaskListCycleMembership.objects.filter(
            cycle=self.cycle
        ).order_by("order")

        for i, expected in enumerate(memberships):

            #get next to perform (on first cycle through we should get first list)
            next_ = self.cycle.next_for_unit(unit)
            self.assertEqual(next_, expected)

            #now perform the task list
            self.get_instance_for_task_list(next_.task_list,unit)

        #confirm that we have wrapped around to the beginning again
        next_ =  self.cycle.next_for_unit(unit)
        self.assertEqual(next_,memberships[0])

    #----------------------------------------------------------------------
    def test_length(self):
        self.assertEqual(self.NLISTS,len(self.cycle))



if __name__ == "__main__":
    setup_test_environment()
    unittest.main()