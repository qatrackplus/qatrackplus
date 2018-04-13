
from django import forms
from django.core.validators import MaxLengthValidator
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory
from django.forms.widgets import RadioSelect, Select, HiddenInput, NumberInput
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from django.conf import settings

from .. import models
from qatrack.service_log import models as sl_models
from qatrack.service_log.forms import ServiceEventMultipleField
from qatrack.qa import utils

BOOL_CHOICES = [(0, "No"), (1, "Yes")]


class UserFormsetMixin(object):
    """A mixin to add a user object to every form in a formset (and the formset itself)"""

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(UserFormsetMixin, self).__init__(*args, **kwargs)

    def _construct_form(self, *args, **kwargs):
        """add user to all children"""
        form = super(UserFormsetMixin, self)._construct_form(*args, **kwargs)
        form.user = self.user
        return form


class TestInstanceWidgetsMixin(object):
    """
    Mixin to override default TestInstance field widgets and validation
    based on the Test type.
    """

    def clean(self):
        """do some custom form validation"""
        cleaned_data = super(TestInstanceWidgetsMixin, self).clean()

        if self.in_progress:
            return cleaned_data

        skipped = cleaned_data.get("skipped")
        comment = cleaned_data.get("comment")
        value = cleaned_data.get("value", None)
        string_value = cleaned_data.get("string_value", None)

        if self.unit_test_info.test.skip_required():
            # force user to enter value unless skipping test
            if value is None and not string_value and not skipped:
                self._errors["value"] = self.error_class(["Value required if not skipping"])
            elif (value is not None or string_value) and skipped:
                self._errors["value"] = self.error_class(["Clear value if skipping"])

            no_comment_required = (
                self.user.has_perm("qa.can_skip_without_comment") or
                self.unit_test_info.test.skip_without_comment
            )
            if not no_comment_required and skipped and not comment:
                self._errors["skipped"] = self.error_class(["Please add comment when skipping"])
                del cleaned_data["skipped"]

            if value is None and skipped and "value" in self.errors:
                del self.errors["value"]
        else:
            cleaned_data['skipped'] = value is None and not string_value
            if "value" in self.errors:
                del self.errors["value"]

        return cleaned_data

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
            self.fields["string_value"].widget = Select(choices=[("", "")] + self.unit_test_info.test.get_choices())
        elif test_type == models.UPLOAD:
            self.fields["string_value"].widget = HiddenInput()
        else:
            self.fields["value"].widget = NumberInput(attrs={"step": "any"})

        if test_type in (models.BOOLEAN, models.MULTIPLE_CHOICE):
            if hasattr(self, "instance") and self.instance.value is not None:
                self.initial["value"] = int(self.instance.value)

        self.fields["value"].widget.attrs.update(attrs)
        self.fields["string_value"].widget.attrs.update(str_attrs)

    def disable_read_only_fields(self):
        """disable some fields for constant and composite tests"""
        if self.unit_test_info.test.type in (models.CONSTANT, models.COMPOSITE, ):
            self.fields["value"].widget.attrs["readonly"] = "readonly"
        elif self.unit_test_info.test.type in (models.STRING_COMPOSITE,):
            self.fields["string_value"].widget.attrs["readonly"] = "readonly"

    @property
    def attachments_to_process(self):
        from qatrack.attachments.models import Attachment
        to_process = []

        uti_pk = self.unit_test_info.pk

        user_attached = [x for x in self.cleaned_data.get("user_attached", "").split(",") if x]
        for aid in user_attached:
            to_process.append((uti_pk, Attachment.objects.get(pk=aid)))

        return to_process


class CreateTestInstanceForm(TestInstanceWidgetsMixin, forms.Form):

    value = forms.FloatField(required=False, widget=forms.widgets.TextInput(attrs={"class": "qa-input"}))
    string_value = forms.CharField(required=False, validators=[MaxLengthValidator(models.MAX_STRING_VAL_LEN)])

    skipped = forms.BooleanField(required=False, help_text=_("Was this test skipped for some reason (add comment)"))
    comment = forms.CharField(widget=forms.Textarea, required=False, help_text=_("Show or hide comment field"))

    user_attached = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        super(CreateTestInstanceForm, self).__init__(*args, **kwargs)
        self.in_progress = False
        self.fields["comment"].widget.attrs["rows"] = 2

    def set_unit_test_info(self, unit_test_info):
        self.unit_test_info = unit_test_info
        self.set_value_widget()
        self.disable_read_only_fields()

    def get_test_info(self):
        return {
            "reference": self.unit_test_info.reference,
            "tolerance": self.unit_test_info.tolerance,
            "unit_test_info": self.unit_test_info,
            "test": self.unit_test_info.test,
        }


BaseTestInstanceFormSet = forms.formsets.formset_factory(CreateTestInstanceForm, extra=0)


class CreateTestInstanceFormSet(UserFormsetMixin, BaseTestInstanceFormSet):
    """
    Formset for entering all the test values for the TestList that a
    user is performing.
    """

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
                init["value"] = utils.to_precision(uti.test.constant_value, settings.CONSTANT_PRECISION)

            initial.append(init)

        kwargs.update(initial=initial)

        super(CreateTestInstanceFormSet, self).__init__(*args, **kwargs)

        for form, uti in zip(self.forms, unit_test_infos):
            form.set_unit_test_info(uti)


class UpdateTestInstanceForm(TestInstanceWidgetsMixin, forms.ModelForm):

    user_attached = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = models.TestInstance
        fields = ("value", "string_value", "skipped", "comment", "user_attached",)

    def __init__(self, *args, **kwargs):

        super(UpdateTestInstanceForm, self).__init__(*args, **kwargs)
        self.in_progress = self.instance.test_list_instance.in_progress
        self.fields["value"].required = False
        self.unit_test_info = self.instance.unit_test_info
        self.set_value_widget()
        self.disable_read_only_fields()
        self.fields["comment"].widget.attrs["rows"] = 2

    def get_test_info(self):
        return {
            "reference": self.instance.reference,
            "tolerance": self.instance.tolerance,
            "unit_test_info": self.instance.unit_test_info,
            "test": self.instance.unit_test_info.test,
        }


BaseUpdateTestInstanceFormSet = inlineformset_factory(models.TestListInstance, models.TestInstance, form=UpdateTestInstanceForm, extra=0, can_delete=False)


class UpdateTestInstanceFormSet(UserFormsetMixin, BaseUpdateTestInstanceFormSet):
    pass


class ReviewTestInstanceForm(forms.ModelForm):

    class Meta:
        model = models.TestInstance
        fields = ("status", )


BaseReviewTestInstanceFormSet = inlineformset_factory(models.TestListInstance, models.TestInstance, form=ReviewTestInstanceForm, extra=0, can_delete=False)


class ReviewTestInstanceFormSet(UserFormsetMixin, BaseReviewTestInstanceFormSet):
    pass


class BaseTestListInstanceForm(forms.ModelForm):
    """parent form for performing or updating a qa test list"""

    status = forms.ModelChoiceField(
        queryset=models.TestInstanceStatus.objects,
        required=False
    )

    work_completed = forms.DateTimeField(required=False)

    modified = forms.DateTimeField(required=False)

    service_events = ServiceEventMultipleField(queryset=sl_models.ServiceEvent.objects.none(), required=False)
    rtsqa_id = forms.IntegerField(required=False, widget=HiddenInput())
    # now handle saving of qa or service event and link rtsqa

    class Meta:
        model = models.TestListInstance
        exclude = ("day",)

    def __init__(self, *args, **kwargs):

        self.unit = kwargs.pop('unit', None)
        self.rtsqa_id = kwargs.pop('rtsqa', None)

        super(BaseTestListInstanceForm, self).__init__(*args, **kwargs)

        for field in ('work_completed', 'work_started'):
            self.fields[field].widget = forms.widgets.DateTimeInput()

            self.fields[field].widget.format = settings.INPUT_DATE_FORMATS[0]
            self.fields[field].input_formats = settings.INPUT_DATE_FORMATS
            self.fields[field].widget.attrs["title"] = settings.DATETIME_HELP
            self.fields[field].widget.attrs['class'] = 'form-control'
            self.fields[field].help_text = settings.DATETIME_HELP

        self.fields["status"].widget.attrs["class"] = "form-control select2"
        self.fields["work_completed"].widget.attrs["placeholder"] = "optional"
        self.fields['service_events'].widget.attrs.update({'class': 'select2'})

        if self.instance.pk and settings.USE_SERVICE_LOG:
            se_ids = []
            rtsqa_ids = []
            for rtsqa in self.instance.rtsqa_for_tli.all():
                se_ids.append(rtsqa.service_event_id)
                rtsqa_ids.append(rtsqa.id)
            self.initial['rtsqa_id'] = ','.join(str(x) for x in rtsqa_ids)
            se_qs = sl_models.ServiceEvent.objects.filter(pk__in=se_ids)
            self.fields['service_events'].queryset = se_qs
            self.initial['service_events'] = se_qs

        elif self.rtsqa_id and settings.USE_SERVICE_LOG:
            rtsqa = sl_models.ReturnToServiceQA.objects.get(pk=self.rtsqa_id)
            self.fields['service_events'].queryset = sl_models.ServiceEvent.objects.filter(pk=rtsqa.service_event.id)
            self.initial['service_events'] = sl_models.ServiceEvent.objects.filter(pk=rtsqa.service_event.id)
            self.initial['rtsqa_id'] = sl_models.ReturnToServiceQA.objects.get(pk=self.rtsqa_id).id

    def clean(self):
        """validate the work_completed & work_started values"""

        cleaned_data = super(BaseTestListInstanceForm, self).clean()

        for field in ("work_completed", "work_started",):
            if field in self.errors:
                self.errors[field][0] += " %s" % settings.DATETIME_HELP

        work_started = cleaned_data.get("work_started")
        work_completed = cleaned_data.get("work_completed")

        # keep previous work completed date if present
        if not work_completed:
            if not self.instance.pk:
                work_completed = timezone.now().astimezone(timezone.get_current_timezone())
            else:
                work_completed = self.instance.work_completed
            cleaned_data["work_completed"] = work_completed

        if work_started and work_completed:
            if work_completed == work_started:
                cleaned_data["work_completed"] = timezone.now().astimezone(timezone.get_current_timezone())
            elif work_completed < work_started:
                self._errors["work_started"] = self.error_class(["Work started date/time can not be after work completed date/time"])
                del cleaned_data["work_started"]

        if work_started:
            if work_started >= timezone.now().astimezone(timezone.get_current_timezone()):
                self._errors["work_started"] = self.error_class(["Work started date/time can not be in the future"])
                if "work_started" in cleaned_data:
                    del cleaned_data["work_started"]

        return cleaned_data


class CreateTestListInstanceForm(BaseTestListInstanceForm):
    """form for doing qa test list"""

    comment = forms.CharField(widget=forms.Textarea, required=False)
    initiate_service = forms.BooleanField(help_text=_('Initiate service event'), required=False)

    def __init__(self, *args, **kwargs):
        super(CreateTestListInstanceForm, self).__init__(*args, **kwargs)
        self.fields['work_started'].initial = timezone.localtime(timezone.now()).strftime(settings.INPUT_DATE_FORMATS[0])
        self.fields['comment'].widget.attrs['rows'] = '3'
        self.fields['comment'].widget.attrs['placeholder'] = 'Add comment about this set of tests'
        self.fields['comment'].widget.attrs['class'] = 'autosize form-control'


class UpdateTestListInstanceForm(BaseTestListInstanceForm):

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


class ReviewTestListInstanceForm(forms.ModelForm):
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
