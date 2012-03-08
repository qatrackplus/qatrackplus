from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.views.generic import ListView

import models
import views

urlpatterns = patterns('',
    url(r"^validate/([\d+])/$", views.validate, name="validate"),
    url(r"^task_lists/$",
        ListView.as_view(model=models.TaskList),
        name="task_lists"
    ),
    url(r"^task_lists/(\w+)/(\d+)/$", views.UnitFrequencyListView.as_view(), name="qa_by_frequency_unit"),
    url(r"^task_lists/(?P<pk>\d+)/$", views.PerformQAView.as_view(), name="perform_qa"),
    url(r"^task_lists/(\w+)/$", views.UnitGroupedFrequencyListView.as_view(), name="qa_by_frequency"),


)