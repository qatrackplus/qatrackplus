#setup up enviroment so we can run this example file on an empty database
import sys
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "qatrack.settings"
sys.path.append(r"..\\..\\")
import django.test.simple
tr = django.test.simple.DjangoTestSuiteRunner()
tr.setup_databases()
tr.setup_test_environment()

#----------------------------------------------------------------------
#start

from qatrack.qa.models import TaskList, TaskListItem, Category
from qatrack.units.models import Unit, UnitType, Modality
from django.contrib.auth.models import User

#set up a test user
user = User(1, username="test_user")
user.save()

#set up a new unit type
unit_type = UnitType(name="tomo", vendor="AccuRay")
unit_type.save()

#create a new modality
modality = Modality(type="photon",energy=6.)
modality.save()

#create a new unit and add a modality to it
unit = Unit(number=1, name="Unit01")
unit.type = unit_type
unit.save()
unit.modalities.add(modality)
unit.save()
print unit


#set up some test categories
category_types = [
    ("Mechanical", "mechanical", "Mechanical & Safety Tests"),
    ("Dosimetry", "dosimetry", "Dosimetry tests (inluding P & T)"),
    ("Miscellaneous", "misc", "Miscellaneous tests"),
]

for name, slug, desc in category_types:
    cat = Category(name=name,description=desc, slug=slug)
    cat.save()

print Category.objects.all()

#Tests that we can create and modify task lists

task_list = TaskList(
    name="Test Task List",
    description="Foo",
    frequency="daily",
    unit=unit,
    created_by=user,
    modified_by=user
)

task_list.save()

tli1 = TaskListItem(
    name = "task list item 1",
    short_name = "item_1",
    description = "foo",
    procedure = "bar",
    task_type = "simple",
    category = Category.objects.get(slug="mechanical"),
    order = 1,
    created_by=user,
    modified_by=user

)
tli1.save()
tli1.task_lists.add(task_list)
tli1.save()



print task_list.unit
print task_list.tasklistitem_set.all()

