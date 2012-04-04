from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.views.generic import ListView

import models
import views

from qatrack.qa import api
from tastypie.api import Api

v1_api = Api(api_name="v1")
v1_api.register(api.TaskListItemResource())
v1_api.register(api.TaskListItemInstanceResource())
v1_api.register(api.ReferenceResource())
v1_api.register(api.ToleranceResource())

urlpatterns = patterns('',
    url(r"^composite/$", views.CompositeCalculation.as_view(), name="composite"),

    #performing qa
    #url(r"^task_list/$",ListView.as_view(model=models.TaskList), name="task_lists" ),
    url(r"^(?P<frequency>\w+)/task_lists?/$", views.UnitGroupedFrequencyListView.as_view(), name="qa_by_frequency"),
    url(r"^(?P<frequency>\w+)/(?P<type>task_lists?|cycles?)/(?P<pk>\d+)/unit/(?P<unit_number>\d+)$", views.PerformQAView.as_view(), name="perform_qa"),
    url(r"^(?P<frequency>\w+)/task_lists?/unit/(?P<unit_number>\d+)/$", views.UnitFrequencyListView.as_view(), name="qa_by_frequency_unit"),

    #api urls
    url(r"^api/",include(v1_api.urls)),


)