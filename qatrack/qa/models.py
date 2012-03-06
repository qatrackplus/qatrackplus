from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from qatrack.units.models import Unit


#============================================================================
class TaskList(models.Model):
    """Container for a collection of QA :model:`TaskListItem`s"""

    FREQUENCY_CHOICES = (
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("semiannual", "Semi-Ann."),
        ("annual", "Annual"),
        ("other", "Other"),
    )
    name = models.CharField(max_length=256)
    slug = models.SlugField(unique=True, help_text=_("A short unique name for use in the URL of this list"))
    description = models.TextField(help_text=_("A concise description of this task checklist"))
    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES,
        help_text=_("Frequency with which this test is to be performed")
    )

    active = models.BooleanField(help_text=_("Uncheck to disable this list"), default=True)
    unit = models.ForeignKey(Unit)

    task_list_items = models.ManyToManyField("TaskListItem", help_text=_("Which task list items does this list contain"), through="TaskListMembership")

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name="task_list_creator", editable=False)
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, related_name="task_list_modifier", editable=False)

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        return "TaskList(%s)" % self.name


#============================================================================
class TaskListInstance(models.Model):
    """Container for a collection of QA :model:`TaskListItemInstance`s

    When a user completes a task list, a collection of :model:`TaskListItemInstance`s
    are created.  TaskListInstance acts as a containter for the collection
    of values so that they are grouped together and can be queried easily.

    """

    task_list = models.ForeignKey(TaskList)

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name="task_list_instance_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, related_name="task_list_instance_modifier")

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        return "TaskListInstance(%s)" % self.name


#============================================================================
class Status(models.Model):
    """Available statuses for QA items

    Can be used to indicate whether data should be included in trending,
    requires action, should be ignored etc.
    """

    name = models.CharField(max_length=25, help_text=_("Give a concice name for this status"))
    description = models.TextField(null=True, blank=True, help_text=_("Optional description of what this status should be used for"))
    trend = models.BooleanField(help_text=_("Indicate whether this data should be included for trending/analysis purposes"))


#============================================================================
class Category(models.Model):
    """A model used for categorizing :model:`TaskListItem`s"""

    name = models.CharField(max_length=256, unique=True)
    slug = models.SlugField(
        max_length=256, unique=True,
        help_text=_("Unique identifier made of lowercase characters and underscores")
    )
    description = models.TextField(
        help_text=_("Give a brief description of what type of tests should be included in this grouping")
    )

    class Meta:
        verbose_name_plural = "categories"

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        return "Category(%s)" % self.name


#============================================================================
class TaskListItem(models.Model):
    """Task list item to be completed as part of a QA :model:`TaskList`"""

    TASK_TYPE_CHOICES = (
        ("boolean", "Boolean"),
        ("simple", "Simple Numerical"),
        ("composite", "Composite"),
        ("constant", "Constant"),
    )

    name = models.CharField(max_length=256, help_text=_("Name for this task list item"))
    short_name = models.SlugField(max_length=25, help_text=_("A short variable name for this test (to be used in composite calculations)."))
    description = models.TextField(help_text=_("A concise description of what this task list item is for (optional)"))
    procedure = models.TextField(help_text=_("A short description of how to carry out this task"), blank=True, null=True)
    active = models.BooleanField(help_text=_("Uncheck to deactivate this test"), default=True)

    task_type = models.CharField(
        max_length=10, choices=TASK_TYPE_CHOICES, default="boolean",
        help_text=_("Indicate if this test is a %s" % (','.join(x[1].title() for x in TASK_TYPE_CHOICES)))
    )
    constant_value = models.FloatField(help_text=_("Only required for constant value types"), null=True, blank=True)
    calculation_procedure = models.TextField(help_text=_("Snippet of Python code for calculating result of composite value tests"), blank=True, null=True)

    category = models.ForeignKey(Category, help_text=_("Choose a category for this task"))

    order = models.IntegerField(null=True)  # display order in parent task list


    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name="task_list_item_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, related_name="task_list_item_modifier")

    class Meta:
        ordering = ("order", )
    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        return "TaskListItem(%s)" % self.name

#============================================================================
class TaskListItemInstance(models.Model):
    """Measured instance of a :model:`TaskListItem`"""

    passed = models.BooleanField(editable=False)
    status = models.ForeignKey(Status)
    value = models.FloatField(help_text=_("For boolean TaskListItems a value of 0 equals False and any non zero equals True"), null=True)
    skipped = models.BooleanField(help_text=_("Was this test skipped for some reason (add comment)"))
    comment = models.TextField(help_text=_("Add a comment to this task"), null=True, blank=True)

    task_list_instance = models.ForeignKey(TaskListInstance)
    task_list_item = models.ForeignKey(TaskListItem)

#============================================================================
class TaskListMembership(models.Model):
    """
    Model for keeping track of what :model:`TaskListItem` belong to which
    :model:`TaskList`s and which order they are to be placed in
    """

    task_list_item = models.ForeignKey(TaskListItem)
    task_list = models.ForeignKey(TaskList)
    task_list_item_order = models.PositiveIntegerField(help_text="The order this test should be executed in")

    #============================================================================
    class Meta:
        ordering = ("task_list_item_order", )
