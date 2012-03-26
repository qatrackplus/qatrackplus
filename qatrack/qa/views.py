import json
from django.contrib import messages
from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.views.generic import ListView, FormView, View
from django.utils.translation import ugettext as _
from qatrack.qa import models
from qatrack.units.models import Unit, UnitType

import forms

#TODO: Move location of qa/template.html templates (up one level)

class JSONResponseMixin(object):
    """bare bones JSON response mixin taken from Django docs"""
    def render_to_response(self, context):
        """Returns a JSON response containing 'context' as payload"""
        return self.get_json_response(self.convert_context_to_json(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        """Construct an `HttpResponse` object."""
        return HttpResponse(content, content_type='application/json', **httpresponse_kwargs)

    def convert_context_to_json(self, context):
        """Convert the context dictionary into a JSON object"""
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)

#============================================================================
class CompositeCalculation(JSONResponseMixin, View):
    """validate all qa items in the request for the :model:`TaskList` with id task_list_id"""

    #----------------------------------------------------------------------
    def get_json_data(self,name):
        """return python data from GET json data"""
        json_string = self.request.POST.get(name)
        if not json_string:
            return

        try:
            return json.loads(json_string)
        except (KeyError, ValueError):
            return

    #----------------------------------------------------------------------
    def post(self,request, *args, **kwargs):
        """calculate and return all composite values
        Note we use post here because the query strings can get very long and
        we may run into browser limits with GET.
        """
        self.values = self.get_json_data("qavalues")
        if not self.values:
            self.render_to_response({"success":False,"errors":["Invalid QA Values"]})

        self.composite_ids = self.get_json_data("composite_ids")
        if not self.composite_ids:
            return self.render_to_response({"success":False,"errors":["No Valid Composite ID's"]})

        #grab calculation procedures for all the composite tests
        self.composite_items = models.TaskListItem.objects.filter(
            pk__in=self.composite_ids.values()
        ).values_list("short_name", "calculation_procedure")


        results = {}
        for name, procedure in self.composite_items:
            #set up clean calculation context each time so there
            #is no potential conflicts between different composite tests
            self.set_calculation_context()
            try:
                exec procedure in self.calculation_context
                results[name] = {
                    'value':self.calculation_context.pop("result"),
                    'error':None
                }
            except:
                results[name] = {'value':None, 'error':"Invalid Test"}

        return self.render_to_response({"success":True,"errors":[],"results":results})

    #----------------------------------------------------------------------
    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""

        #TODO: at the minimum we need to define some basic tests (mean, stddev etc)
        self.calculation_context = {}

        for short_name,info in self.values.iteritems():
            val = info["current_value"]
            if val is not None:
                try:
                    self.calculation_context[short_name] = float(val)
                except ValueError:
                    pass

#============================================================================
class PerformQAView(FormView):
    """view for users to complete a qa task list"""
    template_name = "perform_task_list.html"

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
                obj.status = models.TaskListItemInstance.UNREVIEWED
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
        unit = get_object_or_404(Unit,number=self.kwargs["unit"])
        if self.request.POST:
            formset = forms.TaskListItemInstanceFormset(task_list,unit, self.request.POST)
        else:
            formset = forms.TaskListItemInstanceFormset(task_list, unit)

        categories = models.Category.objects.all()

        context.update({
            'task_list':task_list,
            'unit':unit,
            'formset':formset,
            'categories':categories,
        })

        return context

#============================================================================
class UnitFrequencyListView(ListView):
    """list daily/monthly/annual task lists for a unit"""

    context_object_name = "task_lists"
    template_name = "frequency_list.html"

    #----------------------------------------------------------------------
    def get_queryset(self):
        """
        return task lists for a specific frequency (daily/monthly etc)
        and specific unit
        """
        return models.UnitTaskLists.objects.filter(unit__number=self.args[1],frequency=self.args[0].lower())


#============================================================================
class UnitGroupedFrequencyListView(ListView):
    """view for grouping all task lists with a certain frequency for all units"""
    template_name = "unit_grouped_frequency_list.html"
    context_object_name = "unit_task_lists"
    #----------------------------------------------------------------------
    def get_queryset(self):
        """grab all task lists with given frequency"""
        return models.UnitTaskLists.objects.filter(frequency=self.args[0].lower())





