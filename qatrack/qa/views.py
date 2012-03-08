import json
from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render,get_object_or_404
from django.views.generic import TemplateView, ListView
from models import TaskList
from qatrack.units.models import Unit, UnitType

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
        task_list = TaskList.objects.get(pk=task_list_id)
    except (TypeError, ValueError, TaskList.DoesNotExist):
        response_dict['status'] = "Invalid Task List ID"
        return HttpResponse(json.dumps(response_dict),mimetype="application/json")



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
        return TaskList.objects.filter(frequency=self.args[0].lower())
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







