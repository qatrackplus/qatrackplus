from django import forms

from django.forms.models import inlineformset_factory

from models import TaskList, TaskListInstance, TaskListItemInstance, TaskListMembership


#============================================================================
class TaskListItemInstanceForm(forms.ModelForm):
    """form used for saving a task list item instance"""

    #----------------------------------------------------------------------
    class Meta:
        model = TaskListItemInstance

#inline formset for listing qa tasks
TaskListItemInstanceFormset = inlineformset_factory(
    TaskListInstance, TaskListItemInstance,
    form=TaskListItemInstanceForm,
    extra=0
)


#============================================================================
class TaskListInstanceForm(forms.ModelForm):
    """parent form for doing qa task list"""

    #----------------------------------------------------------------------
    class Meta:
        model = TaskListInstance