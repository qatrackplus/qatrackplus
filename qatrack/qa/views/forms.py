from django import forms
from django.core.validators import MaxLengthValidator
from django.forms.models import inlineformset_factory
from django.forms.widgets import RadioSelect, Select, HiddenInput
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from django.conf import settings

from .. import models


from qatrack.qa import utils

BOOL_CHOICES = [(0, "No"), (1, "Yes")]


#====================================================================================
class UserFormsetMixin(object):
    """A mixin to add a user object to every form in a formset (and the formset itself)"""

    #----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(UserFormsetMixin, self).__init__(*args, **kwargs)

    #---------------------------------------------------------------------------
    def _construct_forms(self):
        """add user to all children"""
        self.forms = []
        for i in xrange(self.total_form_count()):
            f = self._construct_form(i)
            f.user = self.user
            self.forms.append(f)


#============================================================================
class TestInstanceWidgetsMixin(object):
    """
    Mixin to override default TestInstance field widgets and validation
    based on the Test type.
    """

    #----------------------------------------------------------------------
    def clean(self):
        """do some custom form validation"""
        cleaned_data = super(TestInstanceWidgetsMixin, self).clean()

        if self.in_progress:
            return cleaned_data

        skipped = cleaned_data.get("skipped")
        comment = cleaned_data.get("comment")
        value = cleaned_data.get("value", None)
        string_value = cleaned_data.get("string_value", None)

        # force user to enter value unless skipping test
        if value is None and not string_value and not skipped:
            self._errors["value"] = self.error_class(["Value required if not skipping"])
        elif (value is not None or string_value) and skipped:
            self._errors["value"] = self.error_class(["Clear value if skipping"])

        if not self.user.has_perm("qa.can_skip_without_comment") and skipped and not comment:
            self._errors["skipped"] = self.error_class(["Please add comment when skipping"])
            del cleaned_data["skipped"]

        if value is None and skipped and "value" in self.errors:
            del self.errors["value"]

        return cleaned_data

    #---------------------------------------------------------------------------
    def set_value_widget(self):
        """add custom widget for boolean values (after form has been initialized)"""

        # temp store attributes so they can be restored to reset widget
        self.fields["string_value"].widget.attrs["class"] = "qa-input"
        self.fields["value"].widget.attrs["class"] = "qa-input"
        attrs = self.fields["value"].widget.attrs
        str_attrs = self.fields["string_value"].widget.attrs

        test_type = self.unit_test_info.test.type

        if test_type == models.BOOLEAN:
            self.fields["value"].widget = RadioSelect(choices=BOOL_CHOICES)
        elif test_type == models.MULTIPLE_CHOICE:
            self.fields["value"].widget = Select(choices=[("", "")] + self.unit_test_info.test.get_choices())
        elif test_type == models.UPLOAD:
            self.fields["string_value"].widget = HiddenInput()

        if test_type in (models.BOOLEAN, models.MULTIPLE_CHOICE):
            if hasattr(self, "instance") and self.instance.value is not None:
                self.initial["value"] = int(self.instance.value)

        self.fields["value"].widget.attrs.update(attrs)
        self.fields["string_value"].widget.attrs.update(str_attrs)

    #----------------------------------------------------------------------
    def disable_read_only_fields(self):
        """disable some fields for constant and composite tests"""
        if self.unit_test_info.test.type in (models.CONSTANT, models.COMPOSITE, ):
            self.fields["value"].widget.attrs["readonly"] = "readonly"
        elif self.unit_test_info.test.type in (models.STRING_COMPOSITE,):
            self.fields["string_value"].widget.attrs["readonly"] = "readonly"


#============================================================================
class CreateTestInstanceForm(TestInstanceWidgetsMixin, forms.Form):

    value = forms.FloatField(required=False, widget=forms.widgets.TextInput(attrs={"class": "qa-input"}))
    string_value = forms.CharField(required=False, validators=[MaxLengthValidator(models.MAX_STRING_VAL_LEN)])

    skipped = forms.BooleanField(required=False, help_text=_("Was this test skipped for some reason (add comment)"))
    comment = forms.CharField(widget=forms.Textarea, required=False, help_text=_("Show or hide comment field"))

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(CreateTestInstanceForm, self).__init__(*args, **kwargs)
        self.in_progress = False
        self.fields["comment"].widget.attrs["rows"] = 2

    #----------------------------------------------------------------------
    def set_unit_test_info(self, unit_test_info):
        self.unit_test_info = unit_test_info
        self.set_value_widget()
        self.disable_read_only_fields()

    #----------------------------------------------------------------------
    def get_test_info(self):
        return {
            "reference": self.unit_test_info.reference,
            "tolerance": self.unit_test_info.tolerance,
            "unit_test_info": self.unit_test_info,
            "test": self.unit_test_info.test,
        }


#============================================================================
BaseTestInstanceFormSet = forms.formsets.formset_factory(CreateTestInstanceForm, extra=0)


class CreateTestInstanceFormSet(UserFormsetMixin, BaseTestInstanceFormSet):
    """
    Formset for entering all the test values for the TestList that a
    user is performing.
    """

    #----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """
        Set the UnitTestInfo object for each form in the formset and
        set initial values for any CONSTANT Test type.
        """

        unit_test_infos = kwargs.pop("unit_test_infos")

        initial = []
        for uti in unit_test_infos:

            init = {"value": None}

            if uti.test.type == models.CONSTANT:
                init["value"] = utils.to_precision(uti.test.constant_value, 4)

            initial.append(init)

        kwargs.update(initial=initial)

        super(CreateTestInstanceFormSet, self).__init__(*args, **kwargs)

        for form, uti in zip(self.forms, unit_test_infos):
            form.set_unit_test_info(uti)


#============================================================================
class UpdateTestInstanceForm(TestInstanceWidgetsMixin, forms.ModelForm):

    #============================================================================
    class Meta:
        model = models.TestInstance
        fields = ("value", "string_value", "skipped", "comment",)

    #----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):

        super(UpdateTestInstanceForm, self).__init__(*args, **kwargs)
        self.fields["value"].required = False
        self.unit_test_info = self.instance.unit_test_info
        self.set_value_widget()
        self.disable_read_only_fields()

    #----------------------------------------------------------------------
    def get_test_info(self):
        return {
            "reference": self.instance.reference,
            "tolerance": self.instance.tolerance,
            "unit_test_info": self.instance.unit_test_info,
            "test": self.instance.unit_test_info.test,
        }


#============================================================================
BaseUpdateTestInstanceFormSet = inlineformset_factory(models.TestListInstance, models.TestInstance, form=UpdateTestInstanceForm, extra=0, can_delete=False)


class UpdateTestInstanceFormSet(UserFormsetMixin, BaseUpdateTestInstanceFormSet):
    pass


#============================================================================
class ReviewTestInstanceForm(forms.ModelForm):

    #============================================================================
    class Meta:
        model = models.TestInstance
        fields = ("status", )


#============================================================================
BaseReviewTestInstanceFormSet = inlineformset_factory(models.TestListInstance, models.TestInstance, form=ReviewTestInstanceForm, extra=0, can_delete=False)


class ReviewTestInstanceFormSet(UserFormsetMixin, BaseReviewTestInstanceFormSet):
    pass


#============================================================================
class BaseTestListInstanceForm(forms.ModelForm):
    """parent form for performing or updating a qa test list"""

    status = forms.ModelChoiceField(
        queryset=models.TestInstanceStatus.objects,
        required=False
    )

    work_completed = forms.DateTimeField(required=False)

    modified = forms.DateTimeField(required=False)

    #----------------------------------------------------------------------
    class Meta:
        model = models.TestListInstance
        exclude = ("day",)

    #----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(BaseTestListInstanceForm, self).__init__(*args, **kwargs)

        for field in ("work_completed", "work_started"):
            self.fields[field].widget = forms.widgets.DateTimeInput()
            self.fields[field].widget.format = settings.INPUT_DATE_FORMATS[0]
            self.fields[field].input_formats = settings.INPUT_DATE_FORMATS
            self.fields[field].widget.attrs["title"] = settings.DATETIME_HELP
            self.fields[field].widget.attrs["class"] = "input-medium"
            self.fields[field].help_text = settings.DATETIME_HELP
            self.fields[field].localize = True

        self.fields["status"].widget.attrs["class"] = "input-medium"

        self.fields["work_completed"].widget.attrs["placeholder"] = "optional"

        self.fields["comment"].widget.attrs["rows"] = "4"
        self.fields["comment"].widget.attrs["class"] = "pull-right"
        self.fields["comment"].widget.attrs["placeholder"] = "Add comment about this set of tests"
        self.fields["comment"].widget.attrs.pop("cols")

    #---------------------------------------------------------------------------
    def clean(self):
        """validate the work_completed & work_started values"""

        cleaned_data = super(BaseTestListInstanceForm, self).clean()

        for field in ("work_completed", "work_started",):
            if field in self.errors:
                self.errors[field][0] += " %s" % settings.DATETIME_HELP

        work_started = cleaned_data.get("work_started")
        work_completed = cleaned_data.get("work_completed")

        # keep previous work completed date if present
        if not work_completed and self.instance:
            work_completed = self.instance.work_completed
            cleaned_data["work_completed"] = work_completed

        if work_started and work_completed:
            if work_completed == work_started:
                cleaned_data["work_started"] -= timezone.timedelta(minutes=1)
            elif work_completed < work_started:
                self._errors["work_started"] = self.error_class(["Work started date/time can not be after work completed date/time"])
                del cleaned_data["work_started"]

        if work_started:
            if work_started >= timezone.now().astimezone(timezone.get_current_timezone()):
                self._errors["work_started"] = self.error_class(["Work started date/time can not be in the future"])
                if "work_started" in cleaned_data:
                    del cleaned_data["work_started"]

        return cleaned_data


#============================================================================
class CreateTestListInstanceForm(BaseTestListInstanceForm):
    """form for doing qa test list"""

    #----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(CreateTestListInstanceForm, self).__init__(*args, **kwargs)
        self.fields["work_started"].initial = timezone.now()


#============================================================================
class UpdateTestListInstanceForm(BaseTestListInstanceForm):

    #----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):

        instance = kwargs["instance"]

        # only blank out work_completed if we are continuing an in progress list
        # otherwise maintain work completed date (e.g. we are just updating a
        # test list instance that was completed earlier.
        if instance.in_progress:
            instance.work_completed = None

        # force user to re-check in_progress flag if they want to submit
        # as in_progress again.
        instance.in_progress = False

        super(UpdateTestListInstanceForm, self).__init__(*args, **kwargs)


#============================================================================
class ReviewTestListInstanceForm(forms.ModelForm):
    #----------------------------------------------------------------------
    class Meta:
        model = models.TestListInstance
        fields = ()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(ReviewTestListInstanceForm, self).__init__(*args, **kwargs)

    def clean(self):

        cleaned_data = super(ReviewTestListInstanceForm, self).clean()

        if self.instance.created_by == self.user and not self.user.has_perm('qa.can_review_own_tests'):
            raise ValidationError("You do not have the required permission to review your own tests.")
        return cleaned_data



#============================================================================
class SetReferencesAndTolerancesForm(forms.Form):
    """Form for copying references and tolerances from TestList Unit 'x' to TestList Unit 'y' """

    source_unit = forms.ModelChoiceField(queryset=models.Unit.objects.all())
    content_type = forms.ChoiceField((('', '---------'), ('testlist', 'TestList'), ('testlistcycle', 'TestListCycle')))

    # Populate the testlist field
    testlistchoices = models.TestList.objects.all().order_by("name").values_list("pk", 'name')
    testlistcyclechoices = models.TestListCycle.objects.all().order_by("name").values_list("pk", 'name')
    choices = list(testlistchoices) + list(testlistcyclechoices)
    testlist = forms.ChoiceField(choices, label='Testlist(cycle)')

    # Populate the dest_unit field
    unit_choices = models.Unit.objects.all().values_list('pk', 'name')
    dest_unit = forms.ChoiceField(unit_choices, label='Destination unit')

    def save(self):
        source_unit = self.cleaned_data.get("source_unit")
        dest_unit = models.Unit.objects.get(pk=self.cleaned_data.get("dest_unit"))
        testlist = self.cleaned_data.get("testlist")
        ctype = ContentType.objects.get(model=self.cleaned_data.get("content_type"))

        if self.cleaned_data.get("content_type") == 'testlist':
            tl = models.TestList.objects.get(name=testlist)
        elif self.cleaned_data.get("content_type") == 'testlistcycle':
            tl = models.TestListCycle.objects.get(name=testlist)
        else:
            raise ValidationError(_('Invalid value'), code='invalid')

        utc = models.UnitTestCollection.objects.get(unit=dest_unit, object_id=tl.pk,
                                                    content_type=ctype)
        utc.copy_references(source_unit)
