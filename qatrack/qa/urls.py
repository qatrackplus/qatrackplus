from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.views.generic import ListView

import models
import views

from qatrack.qa import api
from tastypie.api import Api

v1_api = Api(api_name="v1")
resources = [
    api.TestListResource(),
    api.TestResource(),
    api.TestInstanceResource(),
    api.TestListInstanceResource(),
    api.ValueResource(),
    api.FrequencyResource(),
    api.StatusResource(),
    api.ReferenceResource(),
    api.CategoryResource(),
    api.ToleranceResource(),
    api.UnitResource(),
    api.ModalityResource(),
    api.UnitTypeResource(),

]
for resource in resources:
    v1_api.register(resource)


urlpatterns = patterns('',

    #redirect based on user
    #url(r"^user_home/$", views.UserHome.as_view(),name="user_home"),
    url(r"^user_home/$", views.UserBasedTestLists.as_view(),name="user_home"),

    #view for composite calculations via ajax
    url(r"^composite/$", views.CompositeCalculation.as_view(), name="composite"),

    #performing qa
    url(r"^(?P<frequency>\w+)/test_lists?/$", views.UnitGroupedFrequencyListView.as_view(), name="qa_by_frequency"),
    url(r"^(?P<frequency>\w+)/(?P<type>test_lists?|cycles?)/(?P<pk>\d+)/unit/(?P<unit_number>\d+)$", views.PerformQAView.as_view(), name="perform_qa"),
    url(r"^(?P<frequency>\w+)/test_lists?/unit/(?P<unit_number>\d+)/$", views.UnitFrequencyListView.as_view(), name="qa_by_frequency_unit"),

    #api urls
    url(r"^api/",include(v1_api.urls)),

    #review
    url(r"review/$", views.ReviewView.as_view(), name="review"),
    url(r"charts/$", views.ChartView.as_view(), name="charts"),
    url(r"^charts/export/$",views.ExportToCSV.as_view()),
)