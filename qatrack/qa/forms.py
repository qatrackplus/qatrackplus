from django import forms

from django.forms.models import inlineformset_factory
from django.forms.widgets import RadioSelect, Select
from django.utils import timezone
from django.utils.translation import ugettext as _

from django.conf import settings

import models

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
    #----------------------------------------------------------------------
    def clean(self):
        """do some custom form validation"""
        cleaned_data = super(TestInstanceWidgetsMixin, self).clean()

        if self.in_progress:
            return cleaned_data

        skipped = cleaned_data.get("skipped")
        comment = cleaned_data.get("comment")
        value = cleaned_data.get("value")

        # force user to enter value unless skipping test
        if value is None and not skipped:
            self._errors["value"] = self.error_class(["Value required if not skipping"])
        elif value is not None and skipped:
            self._errors["value"] = self.error_class(["Clear value if skipping"])

        if not self.user.has_perm("qa.can_skip_without_comment") and skipped and not comment:
            self._errors["skipped"] = self.error_class(["Please add comment when skipping"])
            del cleaned_data["skipped"]

        if value is None and skipped and "value" in self.errors:
            del self.errors["value"]

        return cleaned_data

    #---------------------------------------------------------------------------
    def set_value_widget(self):
        """add custom widget for boolean values (after form has been """

        # temp store attributes so they can be restored to reset widget
        self.fields["value"].widget.attrs["class"] = "qa-input"
        attrs = self.fields["value"].widget.attrs
        test_type = self.unit_test_info.test.type
        if test_type == models.BOOLEAN:
            self.fields["value"].widget = RadioSelect(choices=BOOL_CHOICES)
        elif test_type == models.MULTIPLE_CHOICE:
            self.fields["value"].widget = Select(choices=[("", "")]+self.unit_test_info.test.get_choices())

        if test_type in (models.BOOLEAN, models.MULTIPLE_CHOICE):
            if hasattr(self, "instance") and self.instance.value is not None:
                self.initial["value"] = int(self.instance.value)

        self.fields["value"].widget.attrs.update(attrs)
    #----------------------------------------------------------------------

    def disable_read_only_fields(self):
        """disable some fields for constant and composite tests"""
        if self.unit_test_info.test.type in (models.CONSTANT, models.COMPOSITE,):
            self.fields["value"].widget.attrs["readonly"] = "readonly"


#============================================================================
class CreateTestInstanceForm(TestInstanceWidgetsMixin, forms.Form):
    value = forms.FloatField(required=False, widget=forms.widgets.TextInput(attrs={"class": "qa-input"}))
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
    #----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        unit_test_infos = kwargs.pop("unit_test_infos")

        initial = []
        for uti in unit_test_infos:
            init = {"value": None}
            if uti.test.type == models.CONSTANT:
                init["value"] = uti.test.constant_value
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
        fields = ("value", "skipped", "comment",)
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

    #----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):

        kwargs["queryset"] = kwargs["queryset"].prefetch_related(
            "reference",
            "unit_test_info__test__category"
        )

        super(UpdateTestInstanceFormSet, self).__init__(*args, **kwargs)

#============================================================================


class ReviewTestInstanceForm(forms.ModelForm):

    #============================================================================
    class Meta:
        model = models.TestInstance
        fields = ("status", )

BaseReviewTestInstanceFormSet = inlineformset_factory(models.TestListInstance, models.TestInstance, form=ReviewTestInstanceForm, extra=0, can_delete=False)


class ReviewTestInstanceFormSet(UserFormsetMixin, BaseReviewTestInstanceFormSet):
    pass

#============================================================================


class BaseTestListInstanceForm(forms.ModelForm):
    """parent form for performing or updating a qa test list"""
    status = forms.ModelChoiceField(
        queryset=models.TestInstanceStatus.objects,
        initial=models.TestInstanceStatus.objects.default,
        required=False
    )

    work_completed = forms.DateTimeField(required=False)

    #----------------------------------------------------------------------
    class Meta:
        model = models.TestListInstance

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
        """"""
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

            if work_completed <= work_started:
                self._errors["work_started"] = self.error_class(["Work started date/time can not be after work completed date/time"])
                del cleaned_data["work_started"]

        elif work_started:
            if work_started >= timezone.make_aware(timezone.datetime.now(), timezone.get_current_timezone()):
                self._errors["work_started"] = self.error_class(["Work started date/time can not be in the future"])
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
