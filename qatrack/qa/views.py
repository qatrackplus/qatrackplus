import json
from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render,get_object_or_404
from django.views.generic.base import View
from models import TaskList

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

