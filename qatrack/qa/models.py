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
from django.utils import timezone
from qatrack import settings
from qatrack.qagroups.models import GroupProfile
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
FREQUENCY_DELTAS = {
    DAILY:timezone.timedelta(days=1),
    WEEKLY:timezone.timedelta(weeks=1),
    MONTHLY:timezone.timedelta(weeks=4),
    SEMIANNUAL:timezone.timedelta(days=365/2),
    ANNUAL:timezone.timedelta(days=365),
}

#test_types
BOOLEAN = "boolean"
NUMERICAL = "numerical"
SIMPLE = "simple"
CONSTANT = "constant"
COMPOSITE = "composite"

TEST_TYPE_CHOICES = (
    (BOOLEAN, "Boolean"),
    (SIMPLE, "Simple Numerical"),
    (CONSTANT, "Constant"),
    (COMPOSITE, "Composite"),
)

#tolerance types
ABSOLUTE = "absolute"
PERCENT = "percent"

TOL_TYPE_CHOICES = (
    (ABSOLUTE, "Absolute"),
    (PERCENT, "Percentage"),
)

REF_TYPE_CHOICES = (
    (NUMERICAL, "Numerical"),
    (BOOLEAN, "Yes / No")
)

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
NO_TOL = "no_tol"

PASS_FAIL_CHOICES = (
    (NOT_DONE,"Not Done"),
    (OK,"OK"),
    (TOLERANCE,"Tolerance"),
    (ACTION,"Action"),
    (NO_TOL,"No Tol Set"),
)

EPSILON = 1E-10
#============================================================================
class Reference(models.Model):
    """Reference values for various QA :model:`Test`s"""

    name = models.CharField(max_length=50, help_text=_("Enter a short name for this reference"))
    type = models.CharField(max_length=15, choices=REF_TYPE_CHOICES,default="numerical")
    value = models.FloatField(help_text=_("For Yes/No tests, enter 1 for Yes and 0 for No"))

    #who created this reference
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,editable=False,related_name="reference_creators")

    #who last modified this reference
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User,editable=False,related_name="reference_modifiers")

    #---------------------------------------------------------------------------
    def __unicode__(self):
        """more helpful interactive display name"""
        if self.type == "yes_no":
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
    name = models.CharField(max_length=50, unique=True, help_text=_("Enter a short name for this tolerance type"))
    type = models.CharField(max_length=20, help_text=_("Select whether this will be an absolute or relative tolerance criteria"),choices=TOL_TYPE_CHOICES)
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
            raise ValueError("Tried to calculate percent diff with a zero reference value")
        return 100.*(instance.value-reference.value)/float(reference.value)
    #----------------------------------------------------------------------
    def test_instance(self,instance,reference):
        """compare a value to reference and determine whether it passes/fails"""

        if instance.test.is_boolean():
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
    """A model used for categorizing :model:`Test`s"""

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
class Test(models.Model):
    """Test to be completed as part of a QA :model:`TestList`"""

    VARIABLE_RE = re.compile("^[a-zA-Z_]+[0-9a-zA-Z_]*$")
    RESULT_RE = re.compile("^result\s*=\s*[(_0-9.a-zA-Z]+.*$",re.MULTILINE)

    name = models.CharField(max_length=256, help_text=_("Name for this test"))
    short_name = models.SlugField(max_length=25, help_text=_("A short variable name for this test (to be used in composite calculations)."))
    description = models.TextField(help_text=_("A concise description of what this test is for (optional)"), blank=True,null=True)
    procedure = models.CharField(max_length=512,help_text=_("Link to document describing how to perform this test"), blank=True, null=True)

    type = models.CharField(
        max_length=10, choices=TEST_TYPE_CHOICES, default="boolean",
        help_text=_("Indicate if this test is a %s" % (','.join(x[1].title() for x in TEST_TYPE_CHOICES)))
    )

    constant_value = models.FloatField(help_text=_("Only required for constant value types"), null=True, blank=True)

    category = models.ForeignKey(Category, help_text=_("Choose a category for this test"))

    calculation_procedure = models.TextField(null=True, blank=True,help_text=_(
        "For Composite Tests Only: Enter a Python snippet for evaluation of this test. The snippet must define a variable called 'result'."
    ))

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False, related_name="test_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, related_name="test_modifier")

    #----------------------------------------------------------------------
    def set_references(self):
        """allow user to go to references in admin interface"""

        url = "%s?"%urlresolvers.reverse("admin:qa_unittestinfo_changelist")
        test_filter = "test__id__exact=%d" % self.pk

        unit_filter = "unit__id__exact=%d"
        info_set = self.unittestinfo_set.all()
        urls = [(info.unit.name, url+test_filter+"&"+ unit_filter%info.unit.pk) for info in info_set]
        link = '<a href="%s">%s</a>'
        all_link = link%(url+test_filter,"All Units")
        links = [link % (url,name) for name,url in urls]

        return "%s (%s)" %(all_link, ", ".join(links))
    set_references.allow_tags = True
    set_references.short_description = "Set references and tolerances for this test"

    #----------------------------------------------------------------------
    def is_boolean(self):
        """Return whether or not this is a boolean test"""
        return self.type == BOOLEAN

    #----------------------------------------------------------------------
    def unit_ref_tol(self,unit):
        """return tuple of (act_low, tol_low, ref, tol_high, act_high)
        where the act_*, tol_* and ref are the current tolerances and references
        for this (test,unit) pair
        """

        unit_info = UnitTestInfo.objects.get(unit=unit,test=self)
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

    #----------------------------------------------------------------------
    def clean_calculation_procedure(self):
        """make sure a valid calculation procedure"""
        errors = []

        if not self.calculation_procedure and self.type != COMPOSITE:
            return

        if self.calculation_procedure and self.type != COMPOSITE:
            errors.append(_("Calculation procedure provided, but Test Type is not Composite"))

        if not self.calculation_procedure and self.type == COMPOSITE:
            errors.append(_("No calculation procedure provided, but Test Type is Composite"))


        if not self.RESULT_RE.findall(self.calculation_procedure):
            errors.append(_('Snippet must contain a result line (e.g. result = my_var/another_var*2)'))

        if errors:
            raise ValidationError({"calculation_procedure":errors})
    #----------------------------------------------------------------------
    def clean_constant_value(self):
        """make sure a constant value is provided if TestType is Constant"""
        errors = []
        if self.constant_value is not None and self.type != CONSTANT:
            errors.append(_("Constant value provided, but Test Type is not constant"))

        if self.constant_value is None and self.type == CONSTANT:
            errors.append(_("Test Type is Constant but no constant value provided"))

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
        """extra validation for Tests"""
        super(Test,self).clean_fields(exclude)
        self.clean_calculation_procedure()
        self.clean_constant_value()
        self.clean_short_name()

    #----------------------------------------------------------------------
    def history_for_unit(self,unit,number=5):
        if isinstance(unit,Unit):
            unit_number = unit.number
        else:
            unit_number = unit
        hist = self.testinstance_set.filter(unit__number=unit_number).order_by("work_completed")
        return [(x.work_completed,x.value, x.pass_fail, x.status) for x in hist[:number]]

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""

        return "%s" % (self.name)


#============================================================================
class UnitTestInfo(models.Model):
    unit = models.ForeignKey(Unit)
    test = models.ForeignKey(Test)
    reference = models.ForeignKey(Reference,verbose_name=_("Current Reference"),null=True, blank=True)
    tolerance = models.ForeignKey(Tolerance,null=True, blank=True)
    active = models.BooleanField(default=True)

    #============================================================================
    class Meta:
        verbose_name_plural = "Set References & Tolerances"
        unique_together = ["test","unit"]
    #----------------------------------------------------------------------
    def clean(self):
        """extra validation for Tests"""
        super(UnitTestInfo,self).clean()
        if None not in (self.reference, self.tolerance):
            if self.tolerance.type == PERCENT and self.reference.value < EPSILON:
                msg = _("Percentage based tolerances can not be used with reference value of zero (0)")
                raise ValidationError(msg)


#============================================================================
class TestListMembership(models.Model):
    """Keep track of ordering for tests within a test list"""
    test_list = models.ForeignKey("TestList")
    test = models.ForeignKey(Test)
    order = models.IntegerField()

    class Meta:
        ordering = ("order",)

    #----------------------------------------------------------------------
    def __unicode__(self):
        return self.test.name

#============================================================================
class TestList(models.Model):
    """Container for a collection of QA :model:`Test`s"""

    name = models.CharField(max_length=256)
    slug = models.SlugField(unique=True, help_text=_("A short unique name for use in the URL of this list"))
    description = models.TextField(help_text=_("A concise description of this test checklist"))

    active = models.BooleanField(help_text=_("Uncheck to disable this list"), default=True)

    tests = models.ManyToManyField("Test", help_text=_("Which tests does this list contain"),through=TestListMembership)

    sublists = models.ManyToManyField("self",
        symmetrical=False,null=True, blank=True,
        help_text=_("Choose any sublists that should be performed as part of this list.")
    )

    assigned_to = models.ForeignKey(GroupProfile,help_text = _("QA group that this test list should nominally be performed by"),null=True)

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name="test_list_creator", editable=False)
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, related_name="test_list_modifier", editable=False)

    #----------------------------------------------------------------------
    def last_completed_instance(self,unit):
        """return the last instance of this test list that was performed"""
        try:
            return self.testlistinstance_set.filter(unit=unit).latest("work_completed")
        except TestListInstance.DoesNotExist:
            return None
    #----------------------------------------------------------------------
    def all_tests(self):
        """returns all tests from this list and sublists"""
        tests = [m.test for m in self.testlistmembership_set.all()]
        for sublist in self.sublists.all():
            tests.extend(sublist.all_tests())

        return tests
    #----------------------------------------------------------------------
    def set_references(self):
        """allow user to go to references in admin interface"""

        url = "%s?"%urlresolvers.reverse("admin:qa_unittestinfo_changelist")
        test_filter = "test__id__in=%s" % (','.join(["%d" % test.pk for test in self.all_tests()]))

        unit_filter = "unit__id__exact=%d"
        unit_info_set = self.unittestlists_set.all()
        urls = [(info.unit.name, url+test_filter+"&"+ unit_filter%info.unit.pk) for info in unit_info_set]
        link = '<a href="%s">%s</a>'
        links = [link % (url,name) for name,url in urls]
        if links:
            return ", ".join(links)
        else:
            return "<em>Currently not assigned to any units</em>"
    set_references.allow_tags = True
    set_references.short_description = "Set references and tolerances for this list"

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        return "TestList(%s)" % self.name

#----------------------------------------------------------------------
#When a new Unit is created, this function will automatically
#create a UnitTestList object for each available frequency
#so that it doesn't have to be done manually through the admin
#interface
@receiver(post_save,sender=Unit)
def new_unit_created(*args, **kwargs):
    """Initialize UnitTestLists for a new Unit"""
    if not kwargs["created"]:
        return

    unit = kwargs["instance"]

    for freq,_ in FREQUENCY_CHOICES:
        unit_test_lists_freq = UnitTestLists(
            frequency = freq,
            unit = unit
        )
        unit_test_lists_freq.save()


#============================================================================
class UnitTestListManager(models.Manager):
    #----------------------------------------------------------------------
    def by_unit(self,unit):
        return self.get_query_set().filter(unit=unit)
    #----------------------------------------------------------------------
    def by_frequency(self,frequency):
        return self.get_query_set().filter(frequency=frequency)
    #----------------------------------------------------------------------
    def by_unit_frequency(self,unit,frequency):
        return self.by_frequency(frequency).filter(unit=unit)

#----------------------------------------------------------------------
def due_date(unit,test_list):
    """return the next due date of a test_list for a given unit"""

    if None in  (unit, test_list,):
        return None

    try:
        unit_test_list = UnitTestLists.objects.get(
            unit = unit, test_lists__pk = test_list.pk
        )
    except UnitTestLists.DoesNotExist:
        return None

    if hasattr(test_list,"cycle"):
        last_instance = test_list.cycle.last_completed_instance(unit)
    else:
        last_instance = test_list.last_completed_instance(unit)
    delta = FREQUENCY_DELTAS[unit_test_list.frequency]
    if last_instance:
        return (last_instance.work_completed + delta)




#============================================================================
class UnitTestLists(models.Model):
    """keeps track of which units should perform which test lists at a given frequency"""

    unit = models.ForeignKey(Unit,editable=False)

    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES,
        help_text=_("Frequency with which this test is to be performed")
    )

    test_lists = models.ManyToManyField(TestList,null=True, blank=True)

    cycles = models.ManyToManyField("TestListCycle", null=True, blank=True)

    objects = UnitTestListManager()

    class Meta:
        unique_together = ("frequency", "unit",)
        verbose_name_plural = _("Choose Unit Test Lists")

    #----------------------------------------------------------------------
    def all_test_lists(self,with_last_instance=False):
        """return all test lists from test_lists and cycles """

        test_lists = list(self.test_lists.all())
        for cycle in self.cycles.all():
            test_lists.extend(list(cycle.test_lists.all()))

        if not with_last_instance:
            return test_lists
        else:
            return [(tl,tl.last_completed_instance(self.unit)) for tl in test_lists]
    #----------------------------------------------------------------------
    def test_lists_and_last_complete(self):
        return [(tl,tl.last_completed_instance(self.unit)) for tl in self.test_lists.all()]
    #----------------------------------------------------------------------
    def cycles_and_last_complete(self):
        """return all cycle objects and last complete instance of each cycle"""
        return [(c,c.last_completed_instance(self.unit)) for c in self.cycles.all()]
    #----------------------------------------------------------------------
    def test_lists_cycles_and_last_complete(self):
        """return all cycle objects and last complete instance of each cycle"""
        return self.test_lists_and_last_complete() + self.cycles_and_last_complete()

    #----------------------------------------------------------------------
    def name(self):
        return self.__unicode__()
    #----------------------------------------------------------------------
    def clean_test_lists(self):
        """ensure test list is only set for one frequency for a given unit"""
        errors = []

        for test_list in self.test_lists.all():
            utls = UnitTestLists.objects.filter(
                unit=self.unit,
                test_lists__pk=test_list.pk
            )
            if utls.count()>1:
                freq = dict(FREQUENCY_CHOICES)[utls[0].frequency]
                msg = _("This test is already performed on a %s basis for this unit" % freq)
                errors.append(msg)
        if errors:
            raise ValidationError({"test_lists":errors})
    #----------------------------------------------------------------------
    def clean_cycles(self):
        """ensure cycle is only set for one frequency for a given unit"""
        errors = []
        for cycle in self.cycles.all():
            utls = UnitTestLists.objects.filter(
                unit=self.unit,
                cycles__pk=cycle.pk
            )
            if utls.count()>1:
                freq = dict(FREQUENCY_CHOICES)[utls[0].frequency]
                msg = _("This cycle is already performed on a %s basis for this unit" % freq)
                errors.append(msg)
        if errors:
            raise ValidationError({"cycles":errors})

    #----------------------------------------------------------------------
    def clean_fields(self,exclude=None):

        super(UnitTestLists,self).clean_fields(exclude)
        self.clean_test_lists()
        self.clean_cycles()


    #----------------------------------------------------------------------
    def __unicode__(self):
        return ("%s %s" %(self.unit.name, self.frequency)).title()


#----------------------------------------------------------------------
def create_unittestinfos(test_list,unit):
    """Create UnitTestInfo objects to hold references and tolerances
    for all tests in a test list that was just added to a Unit
    """

    for test in test_list.all_tests():
        UnitTestInfo.objects.get_or_create(unit = unit,test = test)

#----------------------------------------------------------------------
@receiver(m2m_changed, sender=UnitTestLists.cycles.through)
def unit_cycle_change(*args,**kwargs):
    """When a test list cycle is assigned to a unit, ensure there is a
    UnitTestInfo for every test/unit pair
    """
    if kwargs["action"] == "post_add":
        utl = kwargs["instance"]
        for cycle in utl.cycles.all():
            for test_list in cycle.test_lists.all():
                create_unittestinfos(test_list,utl.unit)

#----------------------------------------------------------------------
@receiver(m2m_changed, sender=UnitTestLists.test_lists.through)
def unit_test_list_change(*args,**kwargs):
    """When a test list is assigned to a unit, ensure there is a
    UnitTestInfo for every test/unit pair
    """
    if kwargs["action"] == "post_add":
        utl = kwargs["instance"]
        for test_list in utl.test_lists.all():
            create_unittestinfos(test_list,utl.unit)

#----------------------------------------------------------------------
@receiver(post_save, sender=TestListMembership)
def test_added_to_list(*args,**kwargs):
    """make sure there are UnitTestInfo objects for all tests (1)

    (1) Note that this can't be done in the TestList.save method because the
    many to many relationships are not updated until after the save method has
    been executed. See http://stackoverflow.com/questions/1925383/issue-with-manytomany-relationships-not-updating-inmediatly-after-save
    """


    tlm = kwargs["instance"]
    unit_test_lists = UnitTestLists.objects.filter(test_lists=tlm.test_list)
    for utl in unit_test_lists:
        UnitTestInfo.objects.get_or_create(unit=utl.unit, test=tlm.test)


##============================================================================
class TestInstance(models.Model):
    """Measured instance of a :model:`Test`"""

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, editable=False)

    pass_fail = models.CharField(max_length=20, choices=PASS_FAIL_CHOICES,editable=False)

    #values set by user
    value = models.FloatField(help_text=_("For boolean Tests a value of 0 equals False and any non zero equals True"), null=True)
    skipped = models.BooleanField(help_text=_("Was this test skipped for some reason (add comment)"))
    comment = models.TextField(help_text=_("Add a comment to this test"), null=True, blank=True)


    #reference used
    reference = models.ForeignKey(Reference,null=True, blank=True)
    tolerance = models.ForeignKey(Tolerance, null=True, blank=True)

    unit = models.ForeignKey(Unit,editable=False)

    test_list_instance = models.ForeignKey("TestListInstance",editable=False)
    test = models.ForeignKey(Test)

    work_completed = models.DateTimeField(default=timezone.now,
        help_text=settings.DATETIME_HELP,
    )


    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False, related_name="test_instance_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, related_name="test_instance_modifier")

    class Meta:
        ordering = ("work_completed",)
        get_latest_by = "work_completed"

    #----------------------------------------------------------------------
    def save(self, *args, **kwargs):
        """set status to unreviewed if not previously set"""
        if not self.status:
            self.status = UNREVIEWED
        self.calculate_pass_fail()
        super(TestInstance,self).save(*args,**kwargs)
    #----------------------------------------------------------------------
    def calculate_pass_fail(self):
        """set pass/fail status of the current value"""

        if self.skipped:
            self.pass_fail = NOT_DONE
        elif self.tolerance:
            self.pass_fail = self.tolerance.test_instance(self,self.reference)
        else:
            #no tolerance set
            self.pass_fail = NO_TOL
    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        try :
            return "TestInstance(test=%s)" % self.test.name
        except :
            return "TestInstance(Empty)"


#============================================================================
class TestListInstanceManager(models.Manager):
    #----------------------------------------------------------------------
    def awaiting_review(self):
        return self.get_query_set().filter(testinstance__status=UNREVIEWED)

#============================================================================
class TestListInstance(models.Model):
    """Container for a collection of QA :model:`TestInstance`s

    When a user completes a test list, a collection of :model:`TestInstance`s
    are created.  TestListInstance acts as a containter for the collection
    of values so that they are grouped together and can be queried easily.

    """

    test_list = models.ForeignKey(TestList, editable=False)
    unit = models.ForeignKey(Unit,editable=False)

    work_completed = models.DateTimeField(default=timezone.now)

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False, related_name="test_list_instance_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, related_name="test_list_instance_modifier")

    objects = TestListInstanceManager()
    class Meta:
        ordering = ("work_completed",)
        get_latest_by = "work_completed"

    #----------------------------------------------------------------------
    def pass_fail_status(self,formatted=False):
        """return string with pass fail status of this qa instance"""
        status = [(status,display,self.testinstance_set.filter(pass_fail=status)) for status,display in PASS_FAIL_CHOICES]
        if not formatted:
            return status
        return ", ".join(["%d %s" %(s.count(),d) for _,d,s in status])
    #----------------------------------------------------------------------
    def status(self,formatted=False):
        """return string with review status of this qa instance"""
        status = [(status,display,self.testinstance_set.filter(status=status)) for status,display in STATUS_CHOICES]
        if not formatted:
            return status
        return ", ".join(["%d %s" %(s.count(),d) for _,d,s in status])

    #---------------------------------------------------------------------------
    def __unicode__(self):
        """more helpful interactive display name"""
        try:
            return "TestListInstance(test_list=%s)"%self.test_list.name
        except:
            return "TestListInstance(Empty)"


#============================================================================
class TestListCycle(models.Model):
    """A basic model for creating a collection of test lists that cycle
    based on the list that was last completed

    NOTE: Currently only supports daily rotation. Support for rotation
    at different frequencies may be added sometime in the future.
    """

    name = models.CharField(max_length=256,help_text=_("The name for this test list cycle"))

    test_lists = models.ManyToManyField(TestList,through="TestListCycleMembership")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, help_text=_("Frequency with which this test list is cycled"))

    assigned_to = models.ForeignKey(GroupProfile,help_text = _("QA group that this test list should nominally be performed by"),null=True)


    #----------------------------------------------------------------------
    def __len__(self):
        """return the number of test_lists"""
        if self.pk:
            return self.test_lists.count()
        else:
            return 0

    #----------------------------------------------------------------------
    def first(self):
        """return first in order membership object for this cycle"""
        try:
            return TestListCycleMembership.objects.get(cycle=self, order=0)
        except TestListCycleMembership.DoesNotExist:
            return None
    #----------------------------------------------------------------------
    def last_completed(self,unit):
        """return the membership object of the last completed test_list
        for this object.
        """

        try:
            last_tli = TestListInstance.objects.filter(
                unit=unit,
                test_list__in=self.test_lists.all()
            ).latest("work_completed")

            last = TestListCycleMembership.objects.get(
                cycle=self,
                test_list=last_tli.test_list
            )

        except:
            last = None

        return last
    #----------------------------------------------------------------------
    def next_for_unit(self,unit):
        """return membership object containing next test list to be completed"""

        last_completed = self.last_completed(unit)
        if not last_completed:
            return self.first()

        ntest_lists = self.test_lists.count()
        next_order = last_completed.order + 1

        if next_order >= ntest_lists:
            return self.first()

        return TestListCycleMembership.objects.get(cycle=self, order=next_order)
    #----------------------------------------------------------------------
    def membership_by_order(self,order):
        """return membership for unit with given order"""
        try:
            return TestListCycleMembership.objects.get(cycle=self, order=order)
        except TestListCycleMembership.DoesNotExist:
            return None

    #----------------------------------------------------------------------
    def last_completed_instance(self, unit):
        """return the last instance of this test list that was performed
        for a given Unit or None if it has never been performed"""
        try:
            return TestListInstance.objects.filter(
                unit=unit,
                test_list__in=self.test_lists.all()
            ).latest("work_completed")
        except TestListInstance.DoesNotExist:
            return None

    #----------------------------------------------------------------------
    def __unicode__(self):
        return _(self.name)


#============================================================================
class TestListCycleMembership(models.Model):
    """M2M model for ordering of test lists within cycle"""

    test_list = models.ForeignKey(TestList)
    cycle = models.ForeignKey(TestListCycle)
    order = models.IntegerField()

    class Meta:
        ordering = ("order",)

        #note the following won't actually work because when saving multiple
        #memberships they can have the same order temporarily when orders are changed
        #unique_together = (("order", "cycle"),)

@receiver(post_save, sender=TestListCycleMembership)
def test_added_to_cycle_member(*args,**kwargs):
    """make sure there are UnitTestInfo objects for all tests (1)

    (1) Note that this can't be done in the TestList.save method because the
    many to many relationships are not updated until after the save method has
    been executed. See http://stackoverflow.com/questions/1925383/issue-with-manytomany-relationships-not-updating-inmediatly-after-save
    """


    tlm = kwargs["instance"]
    unit_test_lists = UnitTestLists.objects.filter(test_lists=tlm.test_list)
    for utl in unit_test_lists:
        for test in tlm.test_list.tests.all():
            UnitTestInfo.objects.get_or_create(unit=utl.unit, test=test)
