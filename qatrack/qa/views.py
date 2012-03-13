import json
from django.contrib import messages
from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render,get_object_or_404
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.utils.translation import ugettext as _
from qatrack.qa import models 
from qatrack.units.models import Unit, UnitType

import forms

#TODO: Move location of qa/template.html templates (up one level)
#----------------------------------------------------------------------
def get_composite_context(request):
    """
    Take a request and return a dictionary containing floats of all test values
    that were not skipped.  Note that the request must be made via GET

    The request comes in with a dictionary of lists of the form

    {
        "mytest": [mytest_id, mytest_value, mytest_skipped],
        "foo": [foo_id, foo_value, foo_skipped],
        ...
        "bar": [bar_id, bar_value, bar_skipped],
    }

    e.g.{ "temperature": [123, 22.0, "false"], "wedge_output": [112, 0, "true"]}
    TODO: give more information regarding the required format for the
    request

    """

    composite_calc_context = {}
    for name,properties in request.GET.iterlists():
        if name not in ("cur_val", "cur_id"):
            id_,val,skipped = properties
            if skipped != 'true':
                try:
                    composite_calc_context[name] = float(val)
                except ValueError:
                    pass
    return composite_calc_context

#----------------------------------------------------------------------
def validate(request, task_list_id):
    """validate all qa items in the request for the :model:`TaskList` with id task_list_id"""

    response_dict = {
        'status': None,
    }

    #retrieve the task list item for the field that just changed
    try:
        task_list = models.TaskList.objects.get(pk=task_list_id)
    except (TypeError, ValueError, models.TaskList.DoesNotExist):
        response_dict['status'] = "Invalid Task List ID"
        return HttpResponse(json.dumps(response_dict),mimetype="application/json")


#============================================================================
class PerformQAView(FormView):
    """view for users to complete a qa task list"""
    template_name = "qa/perform_task_list.html"

    context_object_name = "task_list"
    form_class = forms.TaskListInstanceForm

    #----------------------------------------------------------------------
    def form_valid(self, form):
        """add extra info to the task_list_intance and save all the task_list_items if valid"""
        
        context = self.get_context_data(form=form)
        task_list = context["task_list"]
        formset = context["formset"]        
        
        if formset.is_valid():
            
            #add extra info for task_list_instance
            task_list_instance = form.save(commit=False)
            task_list_instance.task_list = task_list
            task_list_instance.created_by = self.request.user
            task_list_instance.modified_by = self.request.user
            task_list_instance.save()
            
            #all task list item values are validated so now add remaining fields manually and save
            for item_form in formset:
                obj = item_form.save(commit=False)
                obj.task_list_instance = task_list_instance                
                obj.status = models.Status.objects.get(name="unreviewed")
                obj.passed = True
                obj.save()

            #let user know request succeeded and return to unit list
            messages.success(self.request,_("Successfully submitted %s "% task_list.name))            
            url = reverse("qa_by_frequency_unit",args=(task_list.frequency,task_list.unit.number))
            return HttpResponseRedirect(url)
        
        #there was an error in one of the forms
        return self.render_to_response(self.get_context_data(form=form))
                    
    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        """add formset and task list to our template context"""
        context = super(PerformQAView, self).get_context_data(**kwargs)
        
        task_list =  get_object_or_404(models.TaskList,pk=self.kwargs["pk"])        
        
        if self.request.POST:
            formset = forms.TaskListItemInstanceFormset(task_list,self.request.POST)
        else:
            formset = forms.TaskListItemInstanceFormset(task_list)
                
        context.update({'task_list':task_list,'formset':formset})
            
        return context

#============================================================================
class UnitFrequencyListView(ListView):
    """list daily/monthly/annual task lists for a unit"""

    context_object_name = "task_lists"
    template_name = "qa/frequency_list.html"

    #----------------------------------------------------------------------
    def get_queryset(self):
        """
        return task lists for a specific frequency (daily/monthly etc)
        and specific unit
        """
        self.unit = get_object_or_404(Unit, number=self.args[1])
        return self.unit.tasklist_set.filter(frequency=self.args[0].lower())
    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        """add unit to template context"""
        context = super(UnitFrequencyListView, self).get_context_data(**kwargs)
        context["unit"] = self.unit
        context["frequency"] = self.args[0]
        return context


#============================================================================
class UnitGroupedFrequencyListView(ListView):
    """view for grouping all task lists with a certain frequency for all units"""
    template_name = "qa/unit_grouped_frequency_list.html"
    #----------------------------------------------------------------------
    def get_queryset(self):
        """grab all task lists with given frequency"""
        return models.TaskList.objects.filter(frequency=self.args[0].lower())
    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        """add grouped objects to template context"""
        context = super(UnitGroupedFrequencyListView, self).get_context_data(**kwargs)
        unit_types = UnitType.objects.all()

        #organize all task lists into unit type->unit->task list heirarchy
        unit_type_groups = []
        for unit_type in unit_types:
            unit_groups = [(u, self.object_list.filter(unit=u)) for u in unit_type.unit_set.all()]
            unit_type_groups.append((unit_type, unit_groups))
        context["unit_type_groups"] = unit_type_groups

        context["frequency"] = self.args[0]
        return context







