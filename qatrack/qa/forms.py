from django import forms

from django.forms.models import inlineformset_factory, modelformset_factory, model_to_dict
from django.forms.widgets import RadioSelect
from django.contrib import messages
import models


#=======================================================================================
class TaskListItemInstanceForm(forms.ModelForm):
    """Model form for use in a formset of task_list_items within a tasklistinstance"""

    value = forms.FloatField(required=False, widget=forms.widgets.TextInput(attrs={"class":"qa-input"}))
    class Meta:
        model = models.TaskListItemInstance

    #----------------------------------------------------------------------
    def clean(self):
        """do some custom form validation"""

        cleaned_data = super(TaskListItemInstanceForm,self).clean()
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
    def set_initial_fks(self,fieldnames,item_models,initial_objs):
        """limit a group of foreign key choices to given querysets and set to initial_objs"""

        for fieldname,model,initial_obj in zip(fieldnames,item_models,initial_objs):
            if not initial_obj:
                continue
            self.fields[fieldname].queryset = model.objects.filter(pk=initial_obj.pk)
            self.fields[fieldname].initial = initial_obj

#=======================================================================================
BaseTaskListItemInstanceFormset = forms.formsets.formset_factory(TaskListItemInstanceForm,extra=0)
class TaskListItemInstanceFormset(BaseTaskListItemInstanceFormset):
    """Formset for TaskListItemInstances"""

    #----------------------------------------------------------------------
    def __init__(self,task_list, unit,*args,**kwargs):
        """prepopulate the reference, tolerance and task_list_item's for all forms in formset"""


        items = task_list.all_items()

        #since we don't know ahead of time how many task list items there are going to be
        #we have to dynamically set extra for every form. Feels a bit hacky, but I'm not sure how else to do it.
        self.extra = len(items)

        super(TaskListItemInstanceFormset,self).__init__(*args,**kwargs)

        for f, item in zip(self.forms, items):
            info = models.TaskListItemUnitInfo.objects.get(
                task_list_item = item, unit = unit
            )

            self.set_initial_fk_data(f,info)
            self.set_widgets(f,info)
            self.disable_read_only_fields(f,info)
            self.set_constant_values(f,info)

    #----------------------------------------------------------------------
    def disable_read_only_fields(self,form,membership):
        """disable some fields for constant and composite tests"""
        if membership.task_list_item.task_type in ("constant", "composite",):
            for field in ("value", "skipped", "comment",):
                form.fields[field].widget.attrs["readonly"] = "readonly"


    #---------------------------------------------------------------------------
    def set_initial_fk_data(self,form, membership):
        """prepopulate our form ref, tol and task_list_item data"""

        #we need this stuff available on the page, but don't want the user to be able to
        #modify these fields (i.e. they should be rendered as_hidden in templates
        fieldnames = ("reference", "tolerance", "task_list_item",)
        item_models = (models.Reference, models.Tolerance, models.TaskListItem,)
        objects = (membership.reference, membership.tolerance, membership.task_list_item,)
        form.set_initial_fks(fieldnames,item_models,objects)
    #----------------------------------------------------------------------
    def set_constant_values(self,form,membership):
        """set values for constant items"""
        if membership.task_list_item.task_type == "constant":
            form.fields["value"].initial = membership.task_list_item.constant_value

    #---------------------------------------------------------------------------
    def set_widgets(self,form,membership):
        """add custom widget for boolean values"""
        if membership.task_list_item.is_boolean():
            #temp store attributes so they can be restored to reset widget
            attrs = form.fields["value"].widget.attrs
            form.fields["value"].widget = RadioSelect(choices=[(0,"No"),(1,"Yes")])
            form.fields["value"].widget.attrs.update(attrs)


#============================================================================
class TaskListInstanceForm(forms.ModelForm):
    """parent form for doing qa task list"""

    #----------------------------------------------------------------------
    class Meta:
        model = models.TaskListInstance