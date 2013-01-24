from django.conf import settings
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User, Group
from django.utils.translation import ugettext as _
from django.core import urlresolvers
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.dispatch import receiver
from django.db.models.signals import pre_save,post_save, post_delete, m2m_changed
from django.db.models import signals
from django.utils import timezone


from qatrack.units.models import Unit
from qatrack.qa import utils

import re



BOOLEAN = "boolean"
NUMERICAL = "numerical"
SIMPLE = "simple"
CONSTANT = "constant"
COMPOSITE = "composite"
MULTIPLE_CHOICE = "multchoice"

TEST_TYPE_CHOICES = (
    (BOOLEAN, "Boolean"),
    (SIMPLE, "Simple Numerical"),
    (MULTIPLE_CHOICE,"Multiple Choice"),
    (CONSTANT, "Constant"),
    (COMPOSITE, "Composite"),
)

#tolerance types
ABSOLUTE = "absolute"
PERCENT = "percent"

TOL_TYPE_CHOICES = (
    (ABSOLUTE, "Absolute"),
    (PERCENT, "Percentage"),
    (MULTIPLE_CHOICE,"Multiple Choice"),
)

#reference types
REF_TYPE_CHOICES = (
    (NUMERICAL, "Numerical"),
    (BOOLEAN, "Yes / No"),
)


#pass fail choices
NOT_DONE = "not_done"
OK = "ok"
TOLERANCE = "tolerance"
ACTION = "action"
NO_TOL = "no_tol"

ACT_HIGH = "act_high"
ACT_LOW = "act_low"
TOL_HIGH = "tol_high"
TOL_LOW = "tol_low"

PASS_FAIL_CHOICES = (
    (NOT_DONE,"Not Done"),
    (OK,"OK"),
    (TOLERANCE,"Tolerance"),
    (ACTION,"Action"),
    (NO_TOL,"No Tol Set"),
)


#due date choices
NOT_DUE = OK
DUE = TOLERANCE
OVERDUE = ACTION
NEWLIST = NOT_DONE

EPSILON = 1E-10

#============================================================================
class FrequencyManager(models.Manager):
    #----------------------------------------------------------------------
    def frequency_choices(self):
        return self.get_query_set().values_list("slug","name")


#============================================================================
class Frequency(models.Model):
    """Frequencies for performing QA tasks with configurable due dates"""

    name = models.CharField(max_length=50, unique=True, help_text=_("Display name for this frequency"))

    slug = models.SlugField(
        max_length=50, unique=True,
        help_text=_("Unique identifier made of lowercase characters and underscores for this frequency")
    )

    nominal_interval = models.PositiveIntegerField(help_text=_("Nominal number of days between test completions"))
    due_interval = models.PositiveIntegerField(help_text=_("How many days since last completed until a test with this frequency is shown as due"))
    overdue_interval = models.PositiveIntegerField(help_text=_("How many days since last completed until a test with this frequency is shown as over due"))

    objects = FrequencyManager()

    class Meta:
        verbose_name_plural = "frequencies"
        ordering = ("nominal_interval",)
        permissions = (
            ("can_choose_frequency","Choose QA by Frequency"),
        )

    #----------------------------------------------------------------------
    def nominal_delta(self):
        """return datetime delta for nominal interval"""
        if self.nominal_interval is not None:
            return timezone.timedelta(days=self.nominal_interval)
    #---------------------------------------------------------------------------
    def due_delta(self):
        """return datetime delta for nominal interval"""
        if self.due_interval is not None:
            return timezone.timedelta(days=self.due_interval)

    #----------------------------------------------------------------------
    def __unicode__(self):
        return "<Frequency(%s)>" % (self.name)


#============================================================================
class StatusManager(models.Manager):
    """manager for TestInstanceStatus"""

    #----------------------------------------------------------------------
    def default(self):
        """return the default TestInstanceStatus"""
        try:
            return self.get_query_set().get(is_default=True)
        except TestInstanceStatus.DoesNotExist:
            return

class TestInstanceStatus(models.Model):
    """Configurable statuses for QA Tests"""

    name = models.CharField(max_length=50,help_text=_("Display name for this status type"),unique=True)
    slug = models.SlugField(
        max_length=50, unique=True,
        help_text=_("Unique identifier made of lowercase characters and underscores for this status")
    )

    description = models.TextField(
        help_text=_("Give a brief description of what type of test results should be given this status"),
        null=True,blank=True
    )


    is_default = models.BooleanField(
        default=False,
        help_text=_("Check to make this status the default for new Test Instances")
    )

    requires_review = models.BooleanField(
        default=True,
        help_text=_("Check to indicate that Test Instances with this status require further review"),
    )
    requires_comment =  models.BooleanField(
        default = False,
        help_text=_("Check to force users to add a comment to the Test Instances when setting to this status type."),
    )

    export_by_default = models.BooleanField(
        default = True,
        help_text=_("Check to indicate whether tests with this status should be exported by default (e.g. for graphing/control charts)"),
    )

    valid = models.BooleanField(
        default=True,
        help_text=_("If unchecked, data with this status will not be exported and the TestInstance will not be considered a valid completed Test")
    )

    objects = StatusManager()


    class Meta:
        verbose_name_plural = "statuses"


    #----------------------------------------------------------------------
    def save(self, *args, **kwargs):
        """set status to unreviewed if not previously set"""

        cur_default = TestInstanceStatus.objects.default()
        if cur_default is None:
            self.is_default = True
        elif self.is_default:
            cur_default.is_default = False
            cur_default.save()

        super(TestInstanceStatus,self).save(*args,**kwargs)


    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.name



#============================================================================
class Reference(models.Model):
    """Reference values for various QA :model:`Test`s"""

    name = models.CharField(max_length=256, help_text=_("Enter a short name for this reference"))
    type = models.CharField(max_length=15, choices=REF_TYPE_CHOICES,default=NUMERICAL)
    value = models.FloatField(help_text=_("Enter the reference value for this test."))

    #who created this reference
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,editable=False,related_name="reference_creators")

    #who last modified this reference
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User,editable=False,related_name="reference_modifiers")

    #----------------------------------------------------------------------
    def clean_fields(self):
        if self.type == BOOLEAN and self.value not in (0,1):
            raise ValidationError({"value":["Boolean values must be 0 or 1"]})
    #----------------------------------------------------------------------
    def value_display(self):
        if self.value is None:
            return ""
        if self.type == BOOLEAN:
            return "Yes" if int(self.value)==1 else "No"
        return "%.6G" %(self.value)
    #---------------------------------------------------------------------------
    def __unicode__(self):
        """more helpful display name"""
        if self.type == BOOLEAN:
            if self.value == 0:
                return "No"
            elif self.value == 1:
                return "Yes"
            else:
                return "%s (Invalid Boolean)"%(self.name,)

        return "%g"%(self.value)

#============================================================================
class Tolerance(models.Model):
    """
    Model/methods for checking whether a value lies within tolerance
    and action levels
    """
    name = models.CharField(max_length=50, unique=True, help_text=_("Enter a short name for this tolerance type"))
    type = models.CharField(max_length=20, help_text=_("Select whether this will be an absolute or relative tolerance criteria"),choices=TOL_TYPE_CHOICES)
    act_low = models.FloatField(verbose_name=_("Action Low"), help_text=_("Absolute value of lower action level"), null=True,blank=True)
    tol_low = models.FloatField(verbose_name=_("Tolerance Low"), help_text=_("Absolute value of lower tolerance level"), null=True,blank=True)
    tol_high = models.FloatField(verbose_name=_("Tolerance High"), help_text=_("Absolute value of upper tolerance level"), null=True,blank=True)
    act_high = models.FloatField(verbose_name=_("Action High"), help_text=_("Absolute value of upper action level"), null=True, blank=True)

    mc_pass_choices = models.CharField(verbose_name=_("Multiple Choice Pass Values"),max_length=2048,help_text=_("Comma seperated list of choices that are considered passing"),null=True,blank=True)
    mc_tol_choices = models.CharField(verbose_name=_("Multiple Choice Tolerance Values"), max_length=2048,help_text=_("Comma seperated list of choices that are considered at tolerance"),null=True,blank=True)

    #who created this tolerance
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,editable=False,related_name="tolerance_creators")

    #who last modified this tolerance
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User,editable=False,related_name="tolerance_modifiers")

    #---------------------------------------------------------------------------
    def pass_choices(self):
        return self.mc_pass_choices.split(",")
    #---------------------------------------------------------------------------
    def tol_choices(self):
        return self.mc_tol_choices.split(",")

    #---------------------------------------------------------------------------
    def clean_choices(self):
        """make sure choices provided if Tolerance Type is MultipleChoice"""

        errors = []

        if self.type == MULTIPLE_CHOICE:

            if (None, None, None, None) != (self.act_low,self.tol_low,self.tol_high,self.act_high):
                errors.append("Value set for tolerance or action but type is Multiple Choice")

            if self.mc_pass_choices  is None or self.mc_pass_choices.strip()=="":
                errors.append("You must give at least l passing choice for a multiple choice tolerance")
            else:

                pass_choices = [x.strip() for x in self.mc_pass_choices.split(",") if x.strip()]
                self.mc_pass_choices = ",".join(pass_choices)

                if self.mc_tol_choices:
                    tol_choices = [x.strip() for x in self.mc_tol_choices.split(",") if x.strip()]
                else:
                    tol_choices = []

                if tol_choices:
                    self.mc_tol_choices = ",".join(tol_choices)

        elif self.type != MULTIPLE_CHOICE:
            if (self.mc_pass_choices or self.mc_tol_choices):
                errors.append("Value set for pass choices or tolerance choices but type is not Multiple Choice")

        if errors:
            raise ValidationError({"mc_pass_choices":errors})
    #----------------------------------------------------------------------
    def clean_tols(self):
        if self.type  in (ABSOLUTE, PERCENT):
            errors = {}
            check = (ACT_HIGH,ACT_LOW,TOL_HIGH,TOL_LOW,)
            for c in check:
                if getattr(self,c) is None:
                    errors[c] = ["You can not leave this field blank for this test type"]

            if errors:
                raise ValidationError(errors)
    #----------------------------------------------------------------------
    def clean_fields(self,exclude=None):
        """extra validation for Tests"""
        super(Tolerance,self).clean_fields(exclude)
        self.clean_choices()
        self.clean_tols()
    #---------------------------------------------------------------------------
    def tolerances_for_value(self,value):
        """return dict containing tolerances for input value"""

        tols = {ACT_HIGH:None,ACT_LOW:None,TOL_LOW:None,TOL_HIGH:None}
        attrs = tols.keys()

        if value is None:
            return tols
        elif self.type == ABSOLUTE:
            for attr in attrs:
                tols[attr] = value + getattr(self,attr)
        elif self.type == PERCENT:
            for attr in attrs:
                tols[attr] = value*(1.+getattr(self,attr)/100.)
        return tols

    #---------------------------------------------------------------------------
    def __unicode__(self):
        """more helpful interactive display name"""
        vals = (self.name,self.act_low,self.tol_low,self.tol_high,self.act_high)
        if self.type == ABSOLUTE:
            return "%s(%s, %s, %s, %s)" % vals
        elif self.type == PERCENT:
            return "%s(%.1f%%, %.1f%%, %.1f%%, %.1f%%)" % vals
        elif self.type == MULTIPLE_CHOICE:
            return "%s(Multiple Choices)" % self.name


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
    RESULT_RE = re.compile("^result\s*=\s*[(\-+_0-9.a-zA-Z]+.*$",re.MULTILINE)

    name = models.CharField(max_length=256, help_text=_("Name for this test"),unique=True,db_index=True)
    slug = models.SlugField(
        verbose_name="Macro name", max_length=128,
        help_text=_("A short variable name consisting of alphanumeric characters and underscores for this test (to be used in composite calculations). "),
        db_index=True,
    )
    description = models.TextField(help_text=_("A concise description of what this test is for (optional)"), blank=True,null=True)
    procedure = models.CharField(max_length=512,help_text=_("Link to document describing how to perform this test"), blank=True, null=True)

    category = models.ForeignKey(Category, help_text=_("Choose a category for this test"))

    type = models.CharField(
        max_length=10, choices=TEST_TYPE_CHOICES, default=SIMPLE,
        help_text=_("Indicate if this test is a %s" % (','.join(x[1].title() for x in TEST_TYPE_CHOICES)))
    )

    choices = models.CharField(max_length=2048,help_text=_("Comma seperated list of choices for multiple choice test types"),null=True,blank=True)
    constant_value = models.FloatField(help_text=_("Only required for constant value types"), null=True, blank=True)

    calculation_procedure = models.TextField(null=True, blank=True,help_text=_(
        "For Composite Tests Only: Enter a Python snippet for evaluation of this test. The snippet must define a variable called 'result'."
    ))

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False, related_name="test_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, related_name="test_modifier")

    #----------------------------------------------------------------------
    def is_numerical(self):
        """return whether or not this is a numerical test"""
        return self.type in (COMPOSITE,CONSTANT,SIMPLE)
    #----------------------------------------------------------------------
    def is_boolean(self):
        """Return whether or not this is a boolean test"""
        return self.type == BOOLEAN
    #----------------------------------------------------------------------
    def is_mult_choice(self):
        """return True if this is a multiple choice test else, false"""
        return self.type == MULTIPLE_CHOICE
    #---------------------------------------------------------------------------
    def check_test_type(self,field, test_type,display):
        #"""check that correct test type is set"""
        errors = []
        if field is not None and self.type != test_type:
            errors.append(_("%s value provided, but Test Type is not %s" % (display,display)))

        if field is None and self.type == test_type:
            errors.append(_("Test Type is %s but no %s value provided" % (display, display)))
        return errors
    #----------------------------------------------------------------------
    def clean_calculation_procedure(self):
        """make sure a valid calculation procedure"""

        if not self.calculation_procedure and self.type != COMPOSITE:
            return

        errors = self.check_test_type(self.calculation_procedure,COMPOSITE,"Composite")
        self.calculation_procedure = str(self.calculation_procedure)
        if not self.RESULT_RE.findall(self.calculation_procedure):
            errors.append(_('Snippet must contain a result line (e.g. result = my_var/another_var*2)'))

        if self.calculation_procedure.find("__") >= 0:
            errors.append(_('No double underscore methods allowed in calculations'))

        try:
            utils.tokenize_composite_calc(self.calculation_procedure)
        except utils.tokenize.TokenError:
            errors.append(_('Calculation procedure invalid: Possible cause is an unbalanced parenthesis'))

        if errors:
            raise ValidationError({"calculation_procedure":errors})
    #----------------------------------------------------------------------
    def clean_constant_value(self):
        """make sure a constant value is provided if TestType is Constant"""
        errors = self.check_test_type(self.constant_value,CONSTANT, "Constant")
        if errors:
            raise ValidationError({"constant_value":errors})
    #---------------------------------------------------------------------------
    def clean_choices(self):
        """make sure choices provided if TestType is MultipleChoice"""
        errors = self.check_test_type(self.choices,MULTIPLE_CHOICE,"Multiple Choice")
        if self.type != MULTIPLE_CHOICE:
            return
        elif self.choices is None:
            errors.append("You must give at least 1 choice for a multiple choice test")
        else:
            choices = [x.strip() for x in self.choices.strip().split(",") if x.strip()]
            if len(choices) < 1:
                errors.append("You must give at least 1 choice for a multiple choice test")
            else:
                self.choices = ",".join(choices)
        if errors:
            raise ValidationError({"choices":errors})

    #----------------------------------------------------------------------
    def clean_slug(self):
        """make sure slug is valid"""

        errors = []

        if not self.slug:
            errors.append(_("All tests require a macro name"))
        elif not self.VARIABLE_RE.match(self.slug):
            errors.append(_("Macro names must contain only letters, numbers and underscores and start with a letter or underscore"))

        if errors:
            raise ValidationError({"slug":errors})

    #----------------------------------------------------------------------
    def clean_fields(self,exclude=None):
        """extra validation for Tests"""
        super(Test,self).clean_fields(exclude)
        self.clean_calculation_procedure()
        self.clean_constant_value()
        self.clean_slug()
        self.clean_choices()
    #---------------------------------------------------------------------------
    def get_choices(self):
        """return choices for multiple choice tests"""
        if self.type == MULTIPLE_CHOICE:
            cs = self.choices.split(",")
            return zip(range(len(cs)),cs)
    #---------------------------------------------------------------------------
    def get_choice_value(self,choice):
        """return string representing integer choice value"""
        if self.type == MULTIPLE_CHOICE:
            return self.choices.split(",")[int(choice)]

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        return "%s" % (self.name)

#============================================================================
def loaded_from_fixture(kwargs):
    return kwargs.get("raw",False)

@receiver(pre_save,sender=Test)
def on_test_save(*args, **kwargs):
    """Ensure that model validates on save"""
    if not loaded_from_fixture(kwargs):

        test = kwargs["instance"]
        if test.type is not BOOLEAN:
            return

        unit_assignments = UnitTestInfo.objects.filter(test = test)

        for ua in unit_assignments:
            if ua.reference and ua.reference.value not in (0.,1.,):
                raise ValidationError("Can't change test type to %s while this test is still assigned to %s with a non-boolean reference"%(test.type, ua.unit.name))


class UnitTestInfoManager(models.Manager):

    #----------------------------------------------------------------------
    def get_query_set(self):
        return super(UnitTestInfoManager,self).get_query_set()

#============================================================================
class UnitTestInfo(models.Model):
    unit = models.ForeignKey(Unit)
    test = models.ForeignKey(Test)

    reference = models.ForeignKey(Reference,verbose_name=_("Current Reference"),null=True, blank=True,on_delete=models.SET_NULL)
    tolerance = models.ForeignKey(Tolerance,null=True, blank=True,on_delete=models.SET_NULL)

    active = models.BooleanField(help_text=_("Uncheck to disable this test on this unit"), default=True,db_index=True)

    assigned_to = models.ForeignKey(Group,help_text = _("QA group that this test list should nominally be performed by"),null=True, blank=True,on_delete=models.SET_NULL)
    last_instance = models.ForeignKey("TestInstance",null=True, editable=False,on_delete=models.SET_NULL)
    objects = UnitTestInfoManager()
    #============================================================================
    class Meta:
        verbose_name_plural = "Set References & Tolerances"
        unique_together = ["test","unit"]

        permissions = (
            ("can_view_ref_tol","Can view Refs and Tols"),
        )

    #----------------------------------------------------------------------
    def clean(self):
        """extra validation for Tests"""

        super(UnitTestInfo,self).clean()
        if None not in (self.reference, self.tolerance):
            if self.tolerance.type == PERCENT and self.reference.value == 0:
                msg = _("Percentage based tolerances can not be used with reference value of zero (0)")
                raise ValidationError(msg)

        if self.test.type == BOOLEAN:

            if self.reference is not None and self.reference.value not in (0., 1.):
                msg = _("Test type is BOOLEAN but reference value is not 0 or 1")
                raise ValidationError(msg)

            if self.tolerance is not None:
                msg = _("Please leave tolerance blank for boolean tests")
                raise ValidationError(msg)


    #----------------------------------------------------------------------
    def get_history(self,number=5):
        """return last 'number' of instances for this test performed on input unit
        list is ordered in ascending dates
        """
        #hist = TestInstance.objects.filter(unit_test_info=self)
        hist = self.testinstance_set.select_related("status").all().order_by("-work_completed","-pk")
        #hist = hist.select_related("status")
        return [(x.work_completed,x.value, x.pass_fail, x.status) for x in reversed(hist[:number])]
    #----------------------------------------------------------------------
    def __unicode__(self):
        return "UnitTestInfo(%s)"%self.pk
#============================================================================
class TestListMembership(models.Model):
    """Keep track of ordering for tests within a test list"""
    test_list = models.ForeignKey("TestList")
    test = models.ForeignKey(Test)
    order = models.IntegerField(db_index=True)

    class Meta:
        ordering = ("order",)
        unique_together = ("test_list","test",)

    #----------------------------------------------------------------------
    def __unicode__(self):
        return "TestListMembership(pk=%s)"%self.pk


#============================================================================
class TestCollectionInterface(models.Model):
    """abstract base class for Tests collection (i.e. TestList's and TestListCycles"""

    name = models.CharField(max_length=256,db_index=True)
    slug = models.SlugField(unique=True, help_text=_("A short unique name for use in the URL of this list"),db_index=True)
    description = models.TextField(help_text=_("A concise description of this test checklist"),null=True,blank=True)

    assigned_to = generic.GenericRelation(
        "UnitTestCollection",
        content_type_field="content_type",
        object_id_field="object_id",
    )

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_created", editable=False)
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_modified", editable=False)

    class Meta:
        abstract = True

    #----------------------------------------------------------------------
    def get_list(self,day=0):
        return self
    #----------------------------------------------------------------------
    def next_list(self,test_list):
        """Return the list following the input list"""
        return self
    #----------------------------------------------------------------------
    def first(self):
        return self
    #----------------------------------------------------------------------
    def all_tests(self):
        """returns all tests from this list and sublists"""
        return Test.objects.filter(
            testlistmembership__test_list__in = self.all_lists()
        ).distinct().prefetch_related("category")
    #----------------------------------------------------------------------
    def content_type(self):
        """return content type of this object"""
        return ContentType.objects.get_for_model(self)



#============================================================================
class TestList(TestCollectionInterface):
    """Container for a collection of QA :model:`Test`s"""

    tests = models.ManyToManyField("Test", help_text=_("Which tests does this list contain"),through=TestListMembership)

    sublists = models.ManyToManyField("self",
        symmetrical=False,null=True, blank=True,
        help_text=_("Choose any sublists that should be performed as part of this list.")
    )
    #----------------------------------------------------------------------
    def all_lists(self):
        """return query for self and all sublists"""
        return TestList.objects.filter(pk=self.pk) | self.sublists.all()
    #----------------------------------------------------------------------
    def ordered_tests(self):
        """return list of all tests/sublist tests in order"""
        tests = list(self.tests.all().order_by("testlistmembership__order").select_related("category"))
        for sublist in self.sublists.all():
            tests.extend(sublist.ordered_tests())
        return tests

    #----------------------------------------------------------------------
    def __len__(self):
        return 1

    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        return "TestList(%s)" % self.name


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
    def test_lists(self):
        return self.get_query_set().filter(
            content_type=ContentType.objects.get(app_label="qa",model="testlist")
        )
    #----------------------------------------------------------------------
    def by_visibility(self,groups):
        return self.get_query_set().filter(visible_to__in=groups)

#============================================================================
class UnitTestCollection(models.Model):
    """keeps track of which units should perform which test lists at a given frequency"""

    unit = models.ForeignKey(Unit)

    frequency = models.ForeignKey(Frequency, help_text=_("Frequency with which this test list is to be performed"))

    assigned_to = models.ForeignKey(Group,help_text = _("QA group that this test list should nominally be performed by"),null=True)
    visible_to = models.ManyToManyField(Group,help_text=_("Select groups who will be able to see this test collection on this unit"),related_name="test_collection_visibility",default=Group.objects.all)

    active = models.BooleanField(help_text=_("Uncheck to disable this test on this unit"), default=True,db_index=True)

    limit = Q(app_label = 'qa', model = 'testlist') | Q(app_label = 'qa', model = 'testlistcycle')
    content_type = models.ForeignKey(ContentType, limit_choices_to = limit)
    object_id = models.PositiveIntegerField()
    tests_object = generic.GenericForeignKey("content_type","object_id")
    objects = UnitTestListManager()

    last_instance = models.ForeignKey("TestListInstance",null=True,editable=False,on_delete=models.SET_NULL)



    class Meta:
        unique_together = ("unit", "frequency", "content_type","object_id",)
        verbose_name_plural = _("Assign Test Lists to Units")
        ordering = ("testlist__name","testlistcycle__name",)
    #----------------------------------------------------------------------
    def due_date(self):
        """return the next due date of this Unit/TestList pair

        due date for a TestList is calculated as minimum due date of all tests
        making up this list.

        due date for a TestCycle is calculated as the maximum of the due
        dates for its member TestLists
        """

        if self.last_instance:
            return utils.due_date(self.last_instance,self.frequency)

    #----------------------------------------------------------------------
    def due_status(self):
        if self.last_instance:
            return utils.due_status(self.last_instance,self.frequency)
        return NOT_DUE

    #----------------------------------------------------------------------
    def last_done_date(self):
        """return date this test list was last performed"""
        if hasattr(self,"last_instance") and self.last_instance is not None:
            return self.last_instance.work_completed

    #----------------------------------------------------------------------
    def unreviewed_instances(self):
        """return a query set of all TestListInstances for this object that have not been fully reviewed"""
        return self.testlistinstance_set.filter(testinstance__status__requires_review=True).distinct().select_related("test_list")
    #----------------------------------------------------------------------
    def unreviewed_test_instances(self):
        """return query set of all TestInstances for this object"""
        return TestInstance.objects.complete().filter(
            unit_test_info__unit = self.unit,
            unit_test_info__test__in = self.tests_object.all_tests()
        )

    #----------------------------------------------------------------------
    def history(self,number=10):
        """returns the last num_instances performed for this object"""
        return reversed(self.testlistinstance_set.all().order_by("-work_completed","-pk")[:number])

    #----------------------------------------------------------------------
    def next_list(self):
        """return next list to be completed from tests_object"""

        if not hasattr(self,"last_instance") or not self.last_instance:
            return self.tests_object.first()

        return self.tests_object.next_list(self.last_instance.test_list)
    #----------------------------------------------------------------------
    def get_list(self,day=None):
        """return next list to be completed from tests_object"""

        if day is None:
            return self.next_list()

        return self.tests_object.get_list(day)

    #----------------------------------------------------------------------
    def name(self):
        return self.__unicode__()
    #----------------------------------------------------------------------
    def test_objects_name(self):
        return self.tests_object.name
    #----------------------------------------------------------------------
    def __unicode__(self):
        return "UnitTestCollection(%s)"%self.pk


#----------------------------------------------------------------------
def get_or_create_unit_test_info(unit,test,assigned_to=None, active=True):

    uti, created = UnitTestInfo.objects.get_or_create(
        unit = unit,
        test = test,
    )

    if created:
        uti.assigned_to = assigned_to
        uti.active = active
        uti.save()
    return uti

#----------------------------------------------------------------------
def find_assigned_unit_test_collections(collection):
    """take a test collection (eg test list, sub list or test list cycle) and return
    the units that it is a part of
    """


    all_parents = {
        ContentType.objects.get_for_model(collection):[collection],
    }

    parent_types = [x._meta.module_name+"_set" for x in TestCollectionInterface.__subclasses__()]

    for parent_type in parent_types:

        if hasattr(collection, parent_type):
            parents = getattr(collection,parent_type).all()
            if parents.count()>0:
                ct = ContentType.objects.get_for_model(parents[0])
                try:
                    all_parents[ct].extend(list(parents))
                except KeyError:
                    all_parents[ct] = list(parents)

    assigned_utcs = []
    for ct,objects in all_parents.items():
        utcs = UnitTestCollection.objects.filter(
            object_id__in= [x.pk for x in objects],
            content_type = ct,
        ).select_related("unit","assigned_to")
        assigned_utcs.extend(utcs)
    return assigned_utcs

#----------------------------------------------------------------------
def update_unit_test_infos(collection):
    """find out which units this test_list is assigned to and make
    sure there are UnitTestInfo's for each Unit, Test pair"""


    all_tests = collection.all_tests()

    assigned_utcs = find_assigned_unit_test_collections(collection)
    for utc in assigned_utcs:
        existing_uti_units = UnitTestInfo.objects.filter(
            unit= utc.unit,
            test__in = all_tests,
        ).select_related("test")

        existing_tests = [x.test for x in existing_uti_units]
        missing_utis = [x for x in all_tests if x not in existing_tests]
        for test in missing_utis:
            get_or_create_unit_test_info(
                unit=utc.unit,
                test=test,
                assigned_to = utc.assigned_to,
                active = utc.active
            )


#----------------------------------------------------------------------
@receiver(post_save, sender=UnitTestCollection)
def list_assigned_to_unit(*args,**kwargs):
    """UnitTestCollection was saved.  Create UnitTestInfo's for all Tests."""
    if not loaded_from_fixture(kwargs):
        update_unit_test_infos(kwargs["instance"].tests_object)

#----------------------------------------------------------------------
@receiver(post_save, sender=TestListMembership)
def test_added_to_list(*args,**kwargs):
    """
    Test was added to a list (or sublist). Find all units this list
    is performed on and create UnitTestInfo for the Unit, Test pair.
    """
    if (not loaded_from_fixture(kwargs)) :
        update_unit_test_infos(kwargs["instance"].test_list)

#----------------------------------------------------------------------
@receiver(post_save, sender=TestList)
def test_list_saved(*args,**kwargs):
    """TestList was saved. Recreate any UTI's that may have been deleted in past"""
    if not loaded_from_fixture(kwargs):
        update_unit_test_infos(kwargs["instance"])


#============================================================================
class TestInstanceManager(models.Manager):

    #----------------------------------------------------------------------
    def in_progress(self):
        return super(TestInstanceManager,self).filter(in_progress=True)
    #----------------------------------------------------------------------
    def complete(self):
        return models.Manager.get_query_set(self).filter(in_progress=False)

#============================================================================
class TestInstance(models.Model):
    """Measured instance of a :model:`Test`"""

    #review status
    status = models.ForeignKey(TestInstanceStatus)
    review_date = models.DateTimeField(null=True, blank=True,editable=False)
    reviewed_by = models.ForeignKey(User,null=True, blank=True,editable=False)

    #did test pass or fail (or was skipped etc)
    pass_fail = models.CharField(max_length=20, choices=PASS_FAIL_CHOICES,editable=False,db_index=True)

    #values set by user
    value = models.FloatField(help_text=_("For boolean Tests a value of 0 equals False and any non zero equals True"), null=True)
    skipped = models.BooleanField(help_text=_("Was this test skipped for some reason (add comment)"))
    comment = models.TextField(help_text=_("Add a comment to this test"), null=True, blank=True)


    #reference used
    reference = models.ForeignKey(Reference,null=True, blank=True,editable=False,on_delete=models.SET_NULL)
    tolerance = models.ForeignKey(Tolerance, null=True, blank=True,editable=False,on_delete=models.SET_NULL)

    unit_test_info = models.ForeignKey(UnitTestInfo,editable=False)

    #keep track if this test was performed as part of a test list
    test_list_instance = models.ForeignKey("TestListInstance",editable=False, null=True, blank=True)


    work_started = models.DateTimeField(editable=False,db_index=True)

    #when was the work actually performed
    work_completed = models.DateTimeField(default=timezone.now,
        help_text=settings.DATETIME_HELP,db_index=True,
    )
    in_progress = models.BooleanField(default=False,editable=False,db_index=True)

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False, related_name="test_instance_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, related_name="test_instance_modifier")

    objects = TestInstanceManager()

    class Meta:
        ordering = ("work_completed",)
        get_latest_by = "work_completed"
        permissions = (
            ("can_view_history","Can view test history"),
            ("can_review","Can review tests"),
        )

    #----------------------------------------------------------------------
    def save(self, *args, **kwargs):
        """set pass fail status on save"""
        self.calculate_pass_fail()
        super(TestInstance,self).save(*args,**kwargs)
    #----------------------------------------------------------------------
    def difference(self):
        """return difference between instance and reference"""
        return self.value - self.reference.value
    #----------------------------------------------------------------------
    def percent_difference(self):
        """return percent difference between instance and reference"""
        if self.reference.value == 0:
            raise ZeroDivisionError("Tried to calculate percent diff with a zero reference value")
        return 100.*(self.value-self.reference.value)/float(self.reference.value)

    #---------------------------------------------------------------------------
    def bool_pass_fail(self):
        diff = abs(self.reference.value - self.value)
        if diff > EPSILON:
            self.pass_fail = ACTION
        else:
            self.pass_fail = OK
    #---------------------------------------------------------------------------
    def mult_choice_pass_fail(self):
        choice = self.unit_test_info.test.get_choice_value(int(self.value)).lower()
        if choice in [x.lower() for x in self.tolerance.pass_choices()]:
            self.pass_fail = OK
        elif choice in [x.lower() for x in self.tolerance.tol_choices()]:
            self.pass_fail = TOLERANCE
        else:
            self.pass_fail = ACTION

    #---------------------------------------------------------------------------
    def float_pass_fail(self):
        diff = self.calculate_diff()
        right_at_tolerance = utils.almost_equal(self.tolerance.tol_low,diff) or utils.almost_equal(self.tolerance.tol_high,diff)
        right_at_action = utils.almost_equal(self.tolerance.act_low,diff) or utils.almost_equal(self.tolerance.act_high,diff)

        if right_at_tolerance or (self.tolerance.tol_low <= diff <= self.tolerance.tol_high):
            self.pass_fail = OK
        elif right_at_action or (self.tolerance.act_low <= diff <= self.tolerance.tol_low or self.tolerance.tol_high <= diff <= self.tolerance.act_high):
            self.pass_fail = TOLERANCE
        else:
            self.pass_fail = ACTION
    #----------------------------------------------------------------------
    def calculate_diff(self):
        if not (self.tolerance and self.reference and self.unit_test_info.test):
            return

        if self.tolerance.type == ABSOLUTE:
            diff = self.difference()
        else:
            diff = self.percent_difference()
        return diff
    #----------------------------------------------------------------------
    def calculate_pass_fail(self):
        """set pass/fail status of the current value"""

        if self.skipped or (self.value is None and self.in_progress):
            self.pass_fail = NOT_DONE
        elif (self.unit_test_info.test.type ==  BOOLEAN) and self.reference:
            self.bool_pass_fail()
        elif self.unit_test_info.test.type ==  MULTIPLE_CHOICE and self.tolerance:
            self.mult_choice_pass_fail()
        elif self.reference and self.tolerance:
            self.float_pass_fail()
        else:
            #no tolerance and/or reference set
            self.pass_fail = NO_TOL
    #----------------------------------------------------------------------
    def value_display(self):
        if self.skipped:
            return "Skipped"
        elif self.value is None:
            return "Not Done"

        test = self.unit_test_info.test
        if test.is_boolean():
            return "Yes" if int(self.value) == 1 else "No"
        elif test.is_mult_choice():
            return test.get_choice_value(self.value)
        return "%.4g" % self.value
    #----------------------------------------------------------------------
    def diff_display(self):
        display = ""
        if self.unit_test_info.test.is_numerical() and self.value is not None:
            try:
                diff = self.calculate_diff()
                if diff is not None:
                    display = "%.4g" % diff
                    if self.tolerance and self.tolerance.type == PERCENT:
                        display += "%"
            except ZeroDivisionError:
                display = "Zero ref with % diff tol"
        return display
    #----------------------------------------------------------------------
    def __unicode__(self):
        """return display representation of object"""
        return "TestInstance(pk=%s)" % self.pk

#----------------------------------------------------------------------
@receiver(post_save,sender=TestInstance)
def on_test_instance_saved(*args,**kwargs):

    if (not loaded_from_fixture(kwargs)):

        test_instance = kwargs["instance"]
        try:
            latest = TestInstance.objects.complete().filter(
                unit_test_info = test_instance.unit_test_info
            ).latest("work_completed")
        except TestInstance.DoesNotExist:
            latest = None

        test_instance.unit_test_info.last_instance = latest
        test_instance.unit_test_info.save()

#============================================================================
class TestListInstanceManager(models.Manager):

    #----------------------------------------------------------------------
    def unreviewed(self):
        return self.complete().filter(testinstance__status__requires_review=True).distinct()
    #----------------------------------------------------------------------
    def in_progress(self):
        return self.get_query_set().filter(in_progress=True)
    #----------------------------------------------------------------------
    def complete(self):
        return self.get_query_set().filter(in_progress=False)

#============================================================================
class TestListInstance(models.Model):
    """Container for a collection of QA :model:`TestInstance`s

    When a user completes a test list, a collection of :model:`TestInstance`s
    are created.  TestListInstance acts as a containter for the collection
    of values so that they are grouped together and can be queried easily.

    """

    unit_test_collection = models.ForeignKey(UnitTestCollection,editable=False)
    test_list = models.ForeignKey(TestList,editable=False)

    work_started = models.DateTimeField(db_index=True)
    work_completed = models.DateTimeField(default=timezone.now,db_index=True,null=True)

    comment = models.TextField(help_text=_("Add a comment to this set of tests"), null=True, blank=True)

    in_progress = models.BooleanField(help_text=_("Mark this session as still in progress so you can complete later (will not be submitted for review)"),default=False,db_index=True)

    #for keeping a very basic history
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, editable=False, related_name="test_list_instance_creator")
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, related_name="test_list_instance_modifier")


    objects = TestListInstanceManager()
    class Meta:
        ordering = ("work_completed",)
        get_latest_by = "work_completed"
        permissions = (
            ("can_override_date","Can override date"),
            ("can_perform_subset","Can perform subset of tests"),
        )

    #----------------------------------------------------------------------
    def pass_fail_status(self):
        """return string with pass fail status of this qa instance"""
        instances = list(self.testinstance_set.all())
        statuses = [(status,display,[x for x in instances if x.pass_fail == status]) for status,display in PASS_FAIL_CHOICES]
        return [x for x in statuses if len(x[2])>0]

    #----------------------------------------------------------------------
    def duration(self):
        """return timedelta of time from start to completion"""
        return self.work_completed-self.work_started
    #----------------------------------------------------------------------
    def status(self,queryset=None):
        """return string with review status of this qa instance"""
        if queryset is None:
            queryset = self.testinstance_set.prefetch_related("status").all()
        status_types = set([x.status for x in queryset])
        statuses = [(status,[x for x in queryset if x.status == status]) for status in status_types]
        return [x for x in statuses if len(x[1])>0]
    #----------------------------------------------------------------------
    def unreviewed_instances(self):
        return self.testinstance_set.filter(status__requires_review=True)
    #----------------------------------------------------------------------
    def tolerance_tests(self):
        return self.testinstance_set.filter(pass_fail=TOLERANCE)
    #----------------------------------------------------------------------
    def failing_tests(self):
        return self.testinstance_set.filter(pass_fail=ACTION)
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return "TestListInstance(pk=%s)"%self.pk


#----------------------------------------------------------------------
def update_last_instances(test_list_instance):
    try:
        last_instance = TestListInstance.objects.complete().filter(
            unit_test_collection=test_list_instance.unit_test_collection
        ).latest("work_completed")
    except TestListInstance.DoesNotExist:
        last_instance = None
    except UnitTestCollection.DoesNotExist:
        #this will occur when a UnitTestCollection deletion cascades and
        #deletes all test_list_instances associated with it.
        #in that case it doesn't make sense to try to update anything
        return


    cycle_ids = TestListCycle.objects.filter(
        test_lists = test_list_instance.test_list
    ).values_list("pk",flat=True)
    cycle_ct = ContentType.objects.get_for_model(TestListCycle)

    test_list_ids = [test_list_instance.test_list.pk]
    list_ct = ContentType.objects.get_for_model(TestList)

    to_update = [(cycle_ct,cycle_ids), (list_ct,test_list_ids)]

    for ct,object_ids in to_update:
        UnitTestCollection.objects.filter(
            content_type = ct,
            object_id__in = object_ids,
            unit = test_list_instance.unit_test_collection.unit,
        ).update(last_instance=last_instance)

    if last_instance:
        for ti in last_instance.testinstance_set.all():
            ti.unit_test_info.last_instance = ti
            ti.unit_test_info.save()
    else:
        for ti in test_list_instance.testinstance_set.all():
            ti.unit_test_info.last_instance = None
            ti.unit_test_info.save()


#----------------------------------------------------------------------
@receiver(post_save,sender=TestListInstance)
def on_test_list_instance_saved(*args,**kwargs):
    """set last instance for UnitTestInfo"""

    if not loaded_from_fixture(kwargs):
        update_last_instances(kwargs["instance"])

@receiver(post_delete,sender=TestListInstance)
#----------------------------------------------------------------------
def on_test_list_instance_deleted(*args,**kwargs):
    """update last_instance if available"""
    test_list_instance = kwargs["instance"]
    update_last_instances(kwargs["instance"])

#============================================================================
class TestListCycle(TestCollectionInterface):
    """A basic model for creating a collection of test lists that cycle
    based on the list that was last completed

    NOTE: Currently only supports daily rotation. Support for rotation
    at different frequencies may be added sometime in the future.
    """

    #name = models.CharField(max_length=256,help_text=_("The name for this test list cycle"))
    test_lists = models.ManyToManyField(TestList,through="TestListCycleMembership")

    #----------------------------------------------------------------------
    def __len__(self):
        """return the number of test_lists"""
        if self.pk:
            return self.test_lists.count()
        else:
            return 0

    #----------------------------------------------------------------------
    def first(self):
        """return first in order membership obect for this cycle"""
        try:
            return self.testlistcyclemembership_set.get(order=0).test_list
        except TestListCycleMembership.DoesNotExist:
            return None

    #----------------------------------------------------------------------
    def all_lists(self):
        """return queryset for all children lists of this cycle"""
        query = TestList.objects.get_empty_query_set()
        for test_list in self.test_lists.all():
            query |= test_list.all_lists()

        return query.distinct()

    #----------------------------------------------------------------------
    def all_tests(self):
        """return all test members of cycle members"""
        query = Test.objects.get_empty_query_set()
        for test_list in self.test_lists.all():
            query |= test_list.all_tests()
        return query.distinct()
    #----------------------------------------------------------------------
    def get_list(self,day=0):
        """get test list for given day"""
        try:
            membership = self.testlistcyclemembership_set.get(order=day)
            return membership.test_list
        except TestListCycleMembership.DoesNotExist:
            return None
    #----------------------------------------------------------------------
    def next_list(self, test_list):
        """return list folling input list in cycle order"""
        if not test_list:
            return self.first()

        inp_membership = self.testlistcyclemembership_set.get(test_list=test_list)

        if inp_membership.order >= (len(self) - 1):
            return self.first()

        return self.testlistcyclemembership_set.get(order=inp_membership.order+1).test_list

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

    #----------------------------------------------------------------------
    def __unicode__(self):
        return "TestListCycleMembership(pk=%s)"%self.pk
