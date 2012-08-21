from django import forms

from django.forms.models import inlineformset_factory, modelformset_factory, model_to_dict
from django.forms.widgets import RadioSelect, Select
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import ugettext as _
import qatrack.settings as settings

import models

BOOL_CHOICES = [(0,"No"),(1,"Yes")]

#============================================================================
class TestInstanceForm(forms.Form):
    value = forms.FloatField(required=False,widget=forms.widgets.TextInput(attrs={"class":"qa-input"}))
    skipped = forms.BooleanField(required=False,help_text=_("Was this test skipped for some reason (add comment)"))
    comment = forms.CharField(widget=forms.Textarea,required=False,help_text=_("Show or hide comment field"))

    #----------------------------------------------------------------------
    def clean(self):
        """do some custom form validation"""

        cleaned_data = super(TestInstanceForm,self).clean()
        skipped = cleaned_data.get("skipped")
        comment = cleaned_data.get("comment")
        value = cleaned_data.get("value")

        if skipped and not comment:
            self._errors["skipped"] = self.error_class(["Please add comment when skipping"])
            del cleaned_data["skipped"]

        #force user to enter value unless skipping test
        if value is None and not skipped:
            self._errors["value"] = self.error_class(["Value required"])
            del cleaned_data["value"]

        return cleaned_data

    #----------------------------------------------------------------------
    def set_unit_test_info(self,unit_test_info):
        self.unit_test_info = unit_test_info
        self.set_value_widget()
        self.disable_read_only_fields()

    #---------------------------------------------------------------------------
    def set_value_widget(self):
        """add custom widget for boolean values (after form has been """

        #temp store attributes so they can be restored to reset widget
        attrs = self.fields["value"].widget.attrs

        if self.unit_test_info.test.is_boolean():
            self.fields["value"].widget = RadioSelect(choices=BOOL_CHOICES)
        elif self.unit_test_info.test.type == models.MULTIPLE_CHOICE:
            self.fields["value"].widget = Select(choices=[("","")]+self.unit_test_info.test.get_choices())
        self.fields["value"].widget.attrs.update(attrs)
    #----------------------------------------------------------------------
    def disable_read_only_fields(self):
        """disable some fields for constant and composite tests"""
        if self.unit_test_info.test.type in (models.CONSTANT,models.COMPOSITE,):
            self.fields["value"].widget.attrs["readonly"] = "readonly"

BaseTestInstanceFormSet = forms.formsets.formset_factory(TestInstanceForm,extra=0)
class TestInstanceFormSet(BaseTestInstanceFormSet):
    #----------------------------------------------------------------------
    def __init__(self,*args,**kwargs):
        unit_test_infos = kwargs.pop("unit_test_infos")
        initial = []
        for uti in unit_test_infos:
            init = {"value":None}
            if uti.test.type == models.CONSTANT:
                init["value"] = uti.test.constant_value
            initial.append(init)
        kwargs.update(initial=initial)
        super(BaseTestInstanceFormSet,self).__init__(*args,**kwargs)

        for form,uti in zip(self.forms,unit_test_infos):
            form.set_unit_test_info(uti)



#============================================================================
class TestListInstanceForm(forms.ModelForm):
    """parent form for doing qa test list"""
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
    def __init__(self,*args,**kwargs):
        super(TestListInstanceForm,self).__init__(*args,**kwargs)
        self.fields["work_completed"].widget = forms.widgets.DateTimeInput()
        self.fields["work_completed"].widget.format = settings.INPUT_DATE_FORMATS[0]
        self.fields["work_completed"].input_formats = settings.INPUT_DATE_FORMATS
        self.fields["work_completed"].widget.attrs["title"] = settings.DATETIME_HELP
        self.fields["work_completed"].initial = timezone.now()
        self.fields["work_completed"].help_text = settings.DATETIME_HELP
        self.fields["work_completed"].localize = True

