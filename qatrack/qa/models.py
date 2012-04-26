import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from qatrack.units.models import Unit
from django.core import urlresolvers
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

from django.dispatch import receiver
from django.db.models.signals import post_save, m2m_changed
from django.db.models import signals
from qatrack import settings
import re

#global frequency choices
DAILY = "daily"
WEEKLY = "weekly"
MONTHLY = "monthly"
SEMIANNUAL = "semiannual"
ANNUAL = "annual"
OTHER = "other"

FREQUENCY_CHOICES = (
    (DAILY, "Daily"),
    (WEEKLY, "Weekly"),
    (MONTHLY, "Monthly"),
    (SEMIANNUAL, "Semi-Ann."),
    (ANNUAL, "Annual"),
    (OTHER, "Other"),
)

#task_types
BOOLEAN = "boolean"
NUMERICAL = "numerical"
SIMPLE = "simple"
CONSTANT = "constant"
COMPOSITE = "composite"

TASK_TYPE_CHOICES = (
    (BOOLEAN, "Boolean"),
    (SIMPLE, "Simple Numerical"),
    (CONSTANT, "Constant"),
    (COMPOSITE, "Composite"),
)

#tolerance types
ABSOLUTE = "absolute"
PERCENT = "percent"


#status choices
UNREVIEWED = "unreviewed"
APPROVED = "approved"
SCRATCH = "scratch"
REJECTED = "rejected"

STATUS_CHOICES = (
    (UNREVIEWED, "Unreviewed"),
    (APPROVED, "Approved"),
    (SCRATCH, "Scratch"),
    (REJECTED, "Rejected"),
)

#pass fail choices
NOT_DONE = "not_done"
OK = "ok"
TOLERANCE = "tolerance"
ACTION = "action"

PASS_FAIL_CHOICES = (
    (NOT_DONE,"Not Done"),
    (OK,"OK"),
    (TOLERANCE,"Tolerance"),
    (ACTION,"Action"),
)

EPSILON = 1E-10
#============================================================================
class Reference(models.Model):
    """Reference values for various QA :model:`TaskListItem`s"""

    TYPE_CHOICES = ((NUMERICAL, "Numerical"), (BOOLEAN, "Yes / No"))


    name = models.CharField(max_length=50, help_text=_("Enter a short name for this reference"))
    ref_type = models.CharField(max_length=15, choices=TYPE_CHOICES,default="numerical")
    value = models.FloatField(help_text=_("For Yes/No tests, enter 1 for Yes and 0 for No"))

    #units = models.ManyToManyField(Unit, help_text=_("Which units is this reference valid for"))
    #task_list_item = models.ForeignKey(TaskListItem, help_text=_("Which task list item is this reference for"))

    #who created this reference
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,editable=False,related_name="reference_creators")

    #who last modified this reference
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User,editable=False,related_name="reference_modifiers")



    #---------------------------------------------------------------------------
    def __unicode__(self):
        """more helpful interactive display name"""
        if self.ref_type == "yes_no":
            if self.value == 1:
                return self.name
            elif self.value == 0:
                return self.name
            else:
                return "%s (Invalid Boolean)"%(self.name,)

        return "%s=%g"%(self.name,self.value)

#============================================================================
class Tolerance(models.Model):
    """
    Model/methods for checking whether a value lies within tolerance
    and action levels
    """
    TYPE_CHOICES = ((ABSOLUTE, "Absolute"),(PERCENT, "Percentage"),)
    name = models.CharField(max_length=50, unique=True, help_text=_("Enter a short name for this tolerance type"))
    type = models.CharField(max_length=20, help_text=_("Select whether this will be an absolute or relative tolerance criteria"),choices=TYPE_CHOICES)
    act_low = models.FloatField(verbose_name="Action Low", help_text=_("Absolute value of lower action level"), null=True)
    tol_low = models.FloatField(verbose_name="Tolerance Low", help_text=_("Absolute value of lower tolerance level"), null=True)
    tol_high = models.FloatField(verbose_name="Tolerance High", help_text=_("Absolute value of upper tolerance level"), null=True)
    act_high = models.FloatField(verbose_name="Action High", help_text=_("Absolute value of upper action level"), null=True)

    #who created this tolerance
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,editable=False,related_name="tolerance_creators")

    #who last modified this tolerance
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User,editable=False,related_name="tolerance_modifiers")

    #----------------------------------------------------------------------
    def test_boolean(self,instance,reference):
        """test a boolean instance against a reference"""
        if abs(instance.value - reference.value) < EPSILON:
            return OK
        return ACTION
    #----------------------------------------------------------------------
    def difference(self,instance,reference):
        """return difference between instance and reference"""
        return instance.value - reference.value
    #----------------------------------------------------------------------
    def percent_difference(self,instance,reference):
        """return percent difference between instance and reference"""
        if (reference.value < EPSILON):
            return self.difference(instance,reference)
        return 100.*(instance.value-reference.value)/float(reference.value)
    #----------------------------------------------------------------------
    def test_instance(self,instance,reference):
        """compare a value to reference and determine whether it passes/fails"""

        if instance.task_list_item.is_boolean():
            return self.test_boolean(instance,reference)

        if self.type == ABSOLUTE:
            diff = self.difference(instance,reference)
        else:
            diff = self.percent_difference(instance,reference)

        if self.tol_low <= diff <= self.tol_high:
            return OK
        elif self.act_low <= diff <= self.tol_low or self.tol_high <= diff <= self.act_high:
            return TOLERANCE

        return ACTION
    #---------------------------------------------------------------------------
    def __unicode__(self):
        """more helpful interactive display name"""
        return "Tolerance(%s)"%self.name

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

    VARIABLE_RE = re.compile("^[a-zA-Z_]+[0-9a-zA-Z_]*$")
    RESULT_RE = re.compile("^result\s*=\s*[(_0-9.a-zA-Z]+.*$",re.MULTILINE)

    name = models.CharField(max_length=256, help_text=_("Name for this task list item"))
    short_name = models.SlugField(max_length=25, help_text=_("A short variable name for this test (to be used in composite calculations)."))
    description = models.TextField(help_text=_("A concise description of what this task list item is for (optional)"), blank=True,null=True)
    procedure = models.TextField(help_text=_("A short description of how to carry out this task"), blank=True, null=True)

    task_type = models.CharField(
        max_length=10, choices=TASK_TYPE_CHOICES, default="boolean",
        help_text=_("Indicate if this test is a %s" % (','.join(x[1].title() for x in TASK_TYPE_CHOICES)))
    )
    constant_value = models.FloatField(help_text=_("Only required for constant value types"), null=True, blank=True)

    category = models.ForeignKey(Category, help_text=_("Choose a category for this task"))

    calculation_procedure = models.TextField(null=True, blank=True,help_text=_(
        "For Composite Tests Only: Enter a Python snippet for evaluation of this test. The snippet must define a variable called 'result'."
    ))

    #units = models.ManyToManyField(Unit,help_text=_("Choose which units this task should be performed on"))

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False, related_name="task_list_item_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, related_name="task_list_item_modifier")

    #----------------------------------------------------------------------
    def set_references(self):
        """allow user to go to references in admin interface"""
        #/admin/qa/tasklistitemunitinfo/?unit__id__exact=1
        url = "%s?"%urlresolvers.reverse("admin:qa_tasklistitemunitinfo_changelist")
        item_filter = "task_list_item__id__exact=%d" % self.pk

        unit_filter = "unit__id__exact=%d"
        info_set = self.tasklistitemunitinfo_set.all()
        urls = [(info.unit.name, url+item_filter+"&"+ unit_filter%info.unit.pk) for info in info_set]
        link = '<a href="%s">%s</a>'
        all_link = link%(url+item_filter,"All Units")
        links = [link % (url,name) for name,url in urls]

        return "%s (%s)" %(all_link, ", ".join(links))
    set_references.allow_tags = True
    set_references.short_description = "Set references and tolerances for this item"

    #----------------------------------------------------------------------
    def is_boolean(self):
        """Return whether or not this is a boolean test"""
        return self.task_type == BOOLEAN

    #----------------------------------------------------------------------
    def unit_ref_tol(self,unit):
        """return tuple of (act_low, tol_low, ref, tol_high, act_high)
        where the act_*, tol_* and ref are the current tolerances and references
        for this (task_list_item,unit) pair
        """
        unit_info = TaskListItemUnitInfo.objects.filter(unit=unit,task_list=self)
        tol = unit_info.tolerance
        ref = unit_info.reference

        if tol:
            tols = [tol.act_low, tol.tol_low, tol.tol_high, tol.act_high]
        else:
            tols = [None]*4

        if ref:
            val = ref.value
        else:
            val = None

        return tols[:2]+[val]+tols[-2:]



    #---------------------------------------------------------------------------
    def is_boolean(self):
        """return True if this is a boolean test, otherwise False"""
        return self.task_type == "boolean"

    #----------------------------------------------------------------------
    def clean_calculation_procedure(self):
        """make sure a valid calculation procedure"""
        errors = []

        if not self.calculation_procedure and self.task_type != COMPOSITE:
            return

        if self.calculation_procedure and self.task_type != COMPOSITE:
            errors.append(_("Calculation procedure provided, but Task Type is not Composite"))

        if not self.calculation_procedure and self.task_type == COMPOSITE:
            errors.append(_("No calculation procedure provided, but Task Type is Composite"))


        if not self.RESULT_RE.findall(self.calculation_procedure):
            errors.append(_('Snippet must contain a result line (e.g. result = my_var/another_var*2)'))

        if errors:
            raise ValidationError({"calculation_procedure":errors})
    #----------------------------------------------------------------------
    def clean_constant_value(self):
        """make sure a constant value is provided if TaskType is Constant"""
        errors = []
        if self.constant_value is not None and self.task_type != CONSTANT:
            errors.append(_("Constant value provided, but Task Type is not constant"))

        if self.constant_value is None and self.task_type == CONSTANT:
            errors.append(_("Task Type is Constant but no constant value provided"))

        if errors:
            raise ValidationError({"constant_value":errors})

    #----------------------------------------------------------------------
    def clean_short_name(self):
        """make sure short_name is valid"""
        errors = []
        if not self.VARIABLE_RE.match(self.short_name):
            errors.append(_("Short names must contain only letters, numbers and underscores and start with a letter or underscore"))

        if errors:
            raise ValidationError({"short_name":errors})


    #----------------------------------------------------------------------
    def clean_fields(self,exclude=None):
        """extra validation for TaskListItem's"""
        super(TaskListItem,self).clean_fields(exclude)
        self.clean_calculation_procedure()
        self.clean_constant_value()
        self.clean_short_name()

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""

        return "%s" % (self.name)


#============================================================================
class TaskListItemUnitInfo(models.Model):
    unit = models.ForeignKey(Unit)
    task_list_item = models.ForeignKey(TaskListItem)
    reference = models.ForeignKey(Reference,verbose_name=_("Current Reference"),null=True, blank=True)
    tolerance = models.ForeignKey(Tolerance,null=True, blank=True)
    active = models.BooleanField(default=True)

    #============================================================================
    class Meta:
        verbose_name_plural = "Set References & Tolerances"
        unique_together = ["task_list_item","unit"]

#============================================================================
class TaskListMembership(models.Model):
    """Keep track of ordering for tasklistitems within a task list"""
    task_list = models.ForeignKey("TaskList")
    task_list_item = models.ForeignKey(TaskListItem)
    order = models.IntegerField()

    class Meta:
        ordering = ("order",)

    #----------------------------------------------------------------------
    def __unicode__(self):
        return self.task_list_item.name

#============================================================================
class TaskList(models.Model):
    """Container for a collection of QA :model:`TaskListItem`s"""

    name = models.CharField(max_length=256)
    slug = models.SlugField(unique=True, help_text=_("A short unique name for use in the URL of this list"))
    description = models.TextField(help_text=_("A concise description of this task checklist"))

    active = models.BooleanField(help_text=_("Uncheck to disable this list"), default=True)

    task_list_items = models.ManyToManyField("TaskListItem", help_text=_("Which task list items does this list contain"),through=TaskListMembership)

    sublists = models.ManyToManyField("self",
        symmetrical=False,null=True, blank=True,
        help_text=_("Choose any sublists that should be performed as part of this list.")
    )

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name="task_list_creator", editable=False)
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, related_name="task_list_modifier", editable=False)

    #----------------------------------------------------------------------
    def last_completed_instance(self):
        """return the last instance of this task list that was performed"""
        try:
            return self.tasklistinstance_set.latest("work_completed")
        except TaskListInstance.DoesNotExist:
            return None
    #----------------------------------------------------------------------
    def all_items(self):
        """returns all task list items from this list and sublists"""
        items = [m.task_list_item for m in self.tasklistmembership_set.all()]
        for sublist in self.sublists.all():
            items.extend(sublist.all_items())

        return items
    #----------------------------------------------------------------------
    def set_references(self):
        """allow user to go to references in admin interface"""
        #/admin/qa/tasklistitemunitinfo/?unit__id__exact=1
        url = "%s?"%urlresolvers.reverse("admin:qa_tasklistitemunitinfo_changelist")
        item_filter = "task_list_item__id__in=%s" % (','.join(["%d" % item.pk for item in self.all_items()]))

        unit_filter = "unit__id__exact=%d"
        unit_info_set = self.unittasklists_set.all()
        urls = [(info.unit.name, url+item_filter+"&"+ unit_filter%info.unit.pk) for info in unit_info_set]
        link = '<a href="%s">%s</a>'
        links = [link % (url,name) for name,url in urls]

        return ", ".join(links)
    set_references.allow_tags = True
    set_references.short_description = "Set references and tolerances for this list"

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        return "TaskList(%s)" % self.name

#----------------------------------------------------------------------
#When a new Unit is created, this function will automatically
#create a UnitTaskList object for each available frequency
#so that it doesn't have to be done manually through the admin
#interface
@receiver(post_save,sender=Unit)
def new_unit_created(*args, **kwargs):
    """Initialize UnitTaskLists for a new Unit"""
    if not kwargs["created"]:
        return

    unit = kwargs["instance"]

    for freq,_ in FREQUENCY_CHOICES:
        unit_task_lists_freq = UnitTaskLists(
            frequency = freq,
            unit = unit
        )
        unit_task_lists_freq.save()


#============================================================================
class UnitTaskListManager(models.Manager):
    #----------------------------------------------------------------------
    def by_unit(self,unit):
        return self.get_query_set().filter(unit=unit)
    #----------------------------------------------------------------------
    def by_frequency(self,frequency):
        return self.get_query_set().filter(frequency=frequency)
    #----------------------------------------------------------------------
    def by_unit_frequency(self,unit,frequency):
        return self.by_frequency(frequency).filter(unit=unit)

#============================================================================
class UnitTaskLists(models.Model):
    """keeps track of which units should perform which task lists at a given frequency"""

    unit = models.ForeignKey(Unit,editable=False)

    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES,
        help_text=_("Frequency with which this test is to be performed")
    )

    task_lists = models.ManyToManyField(TaskList,null=True, blank=True)

    cycles = models.ManyToManyField("TaskListCycle", null=True, blank=True)

    objects = UnitTaskListManager()

    class Meta:
        unique_together = ("frequency", "unit",)
        verbose_name_plural = _("Choose Unit Task Lists")

    #----------------------------------------------------------------------
    def all_task_lists(self):
        """return all task lists from task_lists and cycles """

        task_lists = list(self.task_lists.all())

        for cycle in self.cycles.all():
            task_lists.extend(list(cycle.task_lists.all()))

        return task_lists
    #----------------------------------------------------------------------
    def lists_and_cycles(self):
        """"""
        for task_list in self.task_lists.all():
            yield task_list
        for cycle in self.cycles.all():
            yield cycle

    #----------------------------------------------------------------------
    def name(self):
        return self.__unicode__()

    #----------------------------------------------------------------------
    def __unicode__(self):
        return ("%s %s" %(self.unit.name, self.frequency)).title()


#----------------------------------------------------------------------
def create_tasklistitemunitinfos(task_list,unit):
    """Create TaskListItemUnitInfo objects to hold references and tolerances
    for all task list items in a task list that was just added to a Unit
    """

    for task_list_item in task_list.all_items():
        TaskListItemUnitInfo.objects.get_or_create(
            unit = unit,
            task_list_item = task_list_item,
        )

#----------------------------------------------------------------------
@receiver(m2m_changed, sender=UnitTaskLists.cycles.through)
def unit_cycle_change(*args,**kwargs):
    """When a task list cycle is assigned to a unit, ensure there is a
    TaskListItemUnitInfo for every task_list_item/unit pair
    """
    if kwargs["action"] == "post_add":
        utl = kwargs["instance"]
        for cycle in utl.cycles.all():
            for task_list in cycle.task_lists.all():
                create_tasklistitemunitinfos(task_list,utl.unit)

#----------------------------------------------------------------------
@receiver(m2m_changed, sender=UnitTaskLists.task_lists.through)
def unit_task_list_change(*args,**kwargs):
    """When a task list is assigned to a unit, ensure there is a
    TaskListItemUnitInfo for every task_list_item/unit pair
    """
    if kwargs["action"] == "post_add":
        utl = kwargs["instance"]
        for task_list in utl.task_lists.all():
            create_tasklistitemunitinfos(task_list,utl.unit)
#----------------------------------------------------------------------
@receiver(m2m_changed, sender=TaskList.task_list_items.through)
def task_list_change(*args,**kwargs):
    """make sure there are UnitTaskListInfo infos for all task list items (1)
    and verify that there are no duplicate short names

    (1) Note that this can't be done in the TaskList.save method because the
    many to many relationships are not updated until after the save method has
    been executed. See http://stackoverflow.com/questions/1925383/issue-with-manytomany-relationships-not-updating-inmediatly-after-save
    """

    if kwargs["action"] == "post_add":
        task_list = kwargs["instance"]
        unit_task_lists = UnitTaskLists.objects.filter(task_lists=task_list)
        for utl in unit_task_lists:
            create_tasklistitemunitinfos(task_list,utl.unit)
    elif kwargs["action"] == "pre_add":
        task_list = kwargs["instance"]

#----------------------------------------------------------------------
def test_bool(value,reference):
    """check whether a boolean value """

##============================================================================
class TaskListItemInstance(models.Model):
    """Measured instance of a :model:`TaskListItem`"""

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, editable=False)

    pass_fail = models.CharField(max_length=20, choices=PASS_FAIL_CHOICES,editable=False)

    #values set by user
    value = models.FloatField(help_text=_("For boolean TaskListItems a value of 0 equals False and any non zero equals True"), null=True)
    skipped = models.BooleanField(help_text=_("Was this test skipped for some reason (add comment)"))
    comment = models.TextField(help_text=_("Add a comment to this task"), null=True, blank=True)


    #reference used
    reference = models.ForeignKey(Reference,null=True, blank=True)
    tolerance = models.ForeignKey(Tolerance, null=True, blank=True)

    unit = models.ForeignKey(Unit,editable=False)

    task_list_instance = models.ForeignKey("TaskListInstance",editable=False)
    task_list_item = models.ForeignKey(TaskListItem)

    work_completed = models.DateTimeField(default=datetime.datetime.now,
        help_text=settings.DATETIME_HELP,
    )

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False, related_name="task_list_item_instance_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, related_name="task_list_item_instance_modifier")

    #----------------------------------------------------------------------
    def save(self, *args, **kwargs):
        """set status to unreviewed if not previously set"""
        if not self.status:
            self.status = self.UNREVIEWED
        self.calculate_pass_fail()
        super(TaskListItemInstance,self).save(*args,**kwargs)
    #----------------------------------------------------------------------
    def calculate_pass_fail(self):
        """set pass/fail status of the current value"""

        if self.skipped:
            self.pass_fail = NOT_DONE
        else:
            self.pass_fail = self.tolerance.test_instance(self,self.reference)

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        try :
            return "TaskListItemInstance(item=%s)" % self.task_list_item.name
        except :
            return "TaskListItemInstance(Empty)"


#============================================================================
class TaskListInstance(models.Model):
    """Container for a collection of QA :model:`TaskListItemInstance`s

    When a user completes a task list, a collection of :model:`TaskListItemInstance`s
    are created.  TaskListInstance acts as a containter for the collection
    of values so that they are grouped together and can be queried easily.

    """

    task_list = models.ForeignKey(TaskList, editable=False)
    unit = models.ForeignKey(Unit,editable=False)

    work_completed = models.DateTimeField(default=datetime.datetime.now)

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False, related_name="task_list_instance_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, related_name="task_list_instance_modifier")

    class Meta:
        ordering = ("created",)
        get_latest_by = "created"

    #----------------------------------------------------------------------
    def status(self):
        """return string with status of this qa instance"""
        return [(status,display,self.tasklistiteminstance_set.filter(pass_fail=status)) for status,display in PASS_FAIL_CHOICES]

    #---------------------------------------------------------------------------
    def __unicode__(self):
        """more helpful interactive display name"""
        try:
            return "TaskListInstance(task_list=%s)"%self.task_list.name
        except:
            return "TaskListInstance(Empty)"


#============================================================================
class CycleManager(models.Manager):
    #----------------------------------------------------------------------
    def by_unit(self,unit):
        return self.get_query_set().filter(units__in=[unit])
    #----------------------------------------------------------------------
    def by_frequency(self,frequency):
        return self.get_query_set().filter()
    #----------------------------------------------------------------------
    def by_unit_frequency(self,unit,frequency):
        return self.get_query_set().filter(units__in=[unit],frequency=frequency)

#============================================================================
class TaskListCycle(models.Model):
    """A basic model for creating a collection of task lists that cycle
    based on the list that was last completed

    NOTE: Currently only supports daily rotation. Support for rotation
    at different frequencies may be added sometime in the future.
    """

    name = models.CharField(max_length=256,help_text=_("The name for this task list cycle"))

    task_lists = models.ManyToManyField(TaskList,through="TaskListCycleMembership")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, help_text=_("Frequency with which this task list is cycled"))

    objects = CycleManager()

    #----------------------------------------------------------------------
    def __len__(self):
        """return the number of task_lists"""
        if self.pk:
            return self.task_lists.count()
        else:
            return 0

    #----------------------------------------------------------------------
    def first(self):
        """return first in order membership object for this cycle"""
        return TaskListCycleMembership.objects.get(cycle=self, order=0)
    #----------------------------------------------------------------------
    def last_completed(self,unit):
        """return the membership object of the last completed task_list
        for this object.
        """

        try:
            last_tli = TaskListInstance.objects.filter(
                unit=unit,
                task_list__in=self.task_lists.all()
            ).latest("work_completed")

            last = TaskListCycleMembership.objects.get(
                cycle=self,
                task_list=last_tli.task_list
            )

        except:
            last = None

        return last
    #----------------------------------------------------------------------
    def next_for_unit(self,unit):
        """return membership object containing next task list to be completed"""

        last_completed = self.last_completed(unit)
        if not last_completed:
            return self.first()

        ntask_lists = self.task_lists.count()
        next_order = last_completed.order + 1

        if next_order >= ntask_lists:
            return self.first()

        return TaskListCycleMembership.objects.get(cycle=self, order=next_order)
    #----------------------------------------------------------------------
    def membership_by_order(self,order):
        """return membership for unit with given order"""
        return TaskListCycleMembership.objects.get(cycle=self, order=order)
    #----------------------------------------------------------------------
    def last_completed_instance(self):
        """return the last instance of this task list that was performed
        or None if it has never been performed"""

        try:
            return TaskListInstance.objects.filter(
                task_list__in = self.task_lists.all()
            ).latest("created")
        except self.DoesNotExist:
            return None

    #----------------------------------------------------------------------
    def __unicode__(self):
        return _(self.name)


#============================================================================
class TaskListCycleMembership(models.Model):
    """M2M model for ordering of task lists within cycle"""

    task_list = models.ForeignKey(TaskList)
    cycle = models.ForeignKey(TaskListCycle)
    order = models.IntegerField()

    class Meta:
        ordering = ("order",)

        #note the following won't actually work because when saving multiple
        #memberships they can have the same order temporarily when orders are changed
        #unique_together = (("order", "cycle"),)

