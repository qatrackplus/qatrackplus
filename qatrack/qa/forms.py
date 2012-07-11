from django import forms

from django.forms.models import inlineformset_factory, modelformset_factory, model_to_dict
from django.forms.widgets import RadioSelect, Select
from django.contrib import messages
from django.utils import timezone
import qatrack.settings as settings

import models


#=======================================================================================
class TestInstanceForm(forms.ModelForm):
    """Model form for use in a formset of tests within a testlistinstance"""

    value = forms.FloatField(required=False, widget=forms.widgets.TextInput(attrs={"class":"qa-input"}))
    class Meta:
        model = models.TestInstance
        exclude = ("work_completed","status")
    #----------------------------------------------------------------------
    def clean(self):
        """do some custom form validation"""

        cleaned_data = super(TestInstanceForm,self).clean()
        skipped = cleaned_data["skipped"]
        comment = cleaned_data["comment"]

        if skipped and not comment:
            self._errors["skipped"] = self.error_class(["Please add comment when skipping"])
            del cleaned_data["skipped"]

        #force user to enter value unless skipping test
        if "value" in cleaned_data:
            value = cleaned_data["value"]
            if value is None and not skipped:
                self._errors["value"] = self.error_class(["Value required"])
                del cleaned_data["value"]

        return cleaned_data
    #---------------------------------------------------------------------------
    def setup_form(self):
        """do initialization once instance is set"""
        if self.instance is None:
            return 
        self.set_value_widget()
        self.disable_read_only_fields()
        self.set_constant_values()
    #---------------------------------------------------------------------------
    def set_value_widget(self):
        """add custom widget for boolean values (after form has been """

        #temp store attributes so they can be restored to reset widget
        attrs = self.fields["value"].widget.attrs
        
        if self.instance.test.is_boolean():
            self.fields["value"].widget = RadioSelect(choices=[(0,"No"),(1,"Yes")])
        elif self.instance.test.type == models.MULTIPLE_CHOICE:
            self.fields["value"].widget = Select(choices=[("","")]+self.instance.test.get_choices())
        self.fields["value"].widget.attrs.update(attrs)
    #----------------------------------------------------------------------
    def disable_read_only_fields(self):
        """disable some fields for constant and composite tests"""
        if self.instance.test.type in (models.CONSTANT,models.COMPOSITE,):
            self.fields["value"].widget.attrs["readonly"] = "readonly"
    #----------------------------------------------------------------------        
    def set_constant_values(self):
        """set values for constant tests"""
        if self.instance.test.type == models.CONSTANT:
            self.initial["value"] = self.instance.test.constant_value

#=======================================================================================
BaseTestInstanceFormset = forms.formsets.formset_factory(TestInstanceForm,extra=0)

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


