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
    def set_initial_fks(self,fieldnames,test_models,initial_objs):
        """limit a group of foreign key choices to given querysets and set to initial_objs"""

        for fieldname,model,initial_obj in zip(fieldnames,test_models,initial_objs):
            if not initial_obj:
                continue
            self.fields[fieldname].queryset = model.objects.filter(pk=initial_obj.pk)
            self.fields[fieldname].initial = initial_obj

#=======================================================================================
BaseTestInstanceFormset = forms.formsets.formset_factory(TestInstanceForm,extra=0)
class TestInstanceFormset(BaseTestInstanceFormset):
    """Formset for TestInstances"""

    #----------------------------------------------------------------------
    def __init__(self,test_list, unit,*args,**kwargs):
        """prepopulate the reference, tolerance and tests for all forms in formset"""


        tests = test_list.all_tests()

        #since we don't know ahead of time how many tests there are going to be
        #we have to dynamically set extra for every form. Feels a bit hacky, but I'm not sure how else to do it.
        self.extra = len(tests)

        super(TestInstanceFormset,self).__init__(*args,**kwargs)

        for f, test in zip(self.forms, tests):
            info = models.UnitTestInfo.objects.get(test=test, unit=unit)

            self.set_initial_fk_data(f,info)
            self.set_widgets(f,info)
            self.disable_read_only_fields(f,info)
            self.set_constant_values(f,info)

            #paste on history...
            f.history = info.history()

    #----------------------------------------------------------------------
    def disable_read_only_fields(self,form,membership):
        """disable some fields for constant and composite tests"""
        if membership.test.type in ("constant", "composite",):
            for field in ("value", ):
                form.fields[field].widget.attrs["readonly"] = "readonly"


    #---------------------------------------------------------------------------
    def set_initial_fk_data(self,form, membership):
        """prepopulate our form ref, tol and test data"""

        #we need this stuff available on the page, but don't want the user to be able to
        #modify these fields (i.e. they should be rendered as_hidden in templates
        fieldnames = ("reference", "tolerance", "test")
        test_models = (models.Reference, models.Tolerance, models.Test)
        objects = (membership.reference, membership.tolerance, membership.test,)
        form.set_initial_fks(fieldnames,test_models,objects)
    #----------------------------------------------------------------------
    def set_constant_values(self,form,membership):
        """set values for constant tests"""
        if membership.test.type == "constant":
            form.fields["value"].initial = membership.test.constant_value

    #---------------------------------------------------------------------------
    def set_widgets(self,form,membership):
        """add custom widget for boolean values"""

        #temp store attributes so they can be restored to reset widget
        attrs = form.fields["value"].widget.attrs

        if membership.test.is_boolean():
            form.fields["value"].widget = RadioSelect(choices=[(0,"No"),(1,"Yes")])
        elif membership.test.type == models.MULTIPLE_CHOICE:
            form.fields["value"].widget = Select(choices=[("","")]+membership.test.get_choices())
        form.fields["value"].widget.attrs.update(attrs)


#============================================================================
class TestListInstanceForm2:
    """"""
    #----------------------------------------------------------------------
    class Meta:
        model = models.TestListInstance


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

        #self.fields["status"].widget = Select(
            #choices=[(s.pk,s.name) for s in models.TestInstanceStatus.objects.all().order_by("-is_default")],
        #)

