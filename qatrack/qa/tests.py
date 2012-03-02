from django.test import TestCase
from django.utils import unittest
from models import TaskList, TaskListItem, Category, History
from qatrack.units.models import Unit, UnitType, Modality

#----------------------------------------------------------------------
def create_units():
    """create some units for testing purposes"""

    unit_type = UnitType(name="tomo", vendor="AccuRay")
    unit_type.save()

    modality = Modality(type="photon",energy=6.)
    modality.save()

    unit = Unit(number=1, name="Unit01")
    unit.type = unit_type
    unit.save()
    unit.modalities.add(modality)
    unit.save()
    return [unit]

class TaskListTest(TestCase):
    #----------------------------------------------------------------------
    def setUp(self):
        """set up required task list groups"""

        self.units = create_units()

        categories = [
            ("Mechanical", "mechanical", "Mechanical & Safety Tests"),
            ("Dosimetry", "dosimetry", "Dosimetry tests (inluding P & T)"),
            ("Miscellaneous", "misc", "Miscellaneous tests"),
        ]

        self.categories = []
        for name, slug, desc in categories:
            cat = Category(name=name,description=desc, slug=slug)
            cat.save()

        self.categories = Category.objects.all()

    def test_basic_operations(self):
        """
        Tests that we can create and modify task lists
        """

        task_list = TaskList(
            name = "Test Task List",
            description = "Foo",
            frequency = "daily",
        )

        history = History()
        history.save()
        task_list.history = history
        task_list.save()

        task_list.units.add(*self.units)

        history_tli = History()
        history_tli.save()

        tli1 = TaskListItem(
            name = "task list item 1",
            short_name = "item_1",
            description = "foo",
            procedure = "bar",
            task_type = "simple",
            category = Category.objects.get(slug="mechanical"),
            order = 1,
            history = history_tli
        )
        tli1.save()
        tli1.task_lists.add(task_list)
        tli1.save()

        print task_list.units.all()
        print task_list.tasklistitem_set.all()


if __name__ == "__main__":
    unittest.main()