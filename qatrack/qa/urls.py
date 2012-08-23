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

    url(r"^$", views.AllTestCollections.as_view(),name="all_lists"),

    #view for composite calculations via ajax
    url(r"^composite/$", views.CompositeCalculation.as_view(), name="composite"),


    #api urls
    url(r"^api/",include(v1_api.urls)),

    #review
    url(r"review/$", views.ReviewView.as_view(), name="review"),
    url(r"review/new/$", views.AwaitingReview.as_view(), name="awaiting_review"),
    url(r"review/details/(?P<pk>\d+)/$", views.ReviewTestListInstance.as_view(), name="review_test_list_instance"),
    url(r"charts/$", views.ChartView.as_view(), name="charts"),
    url(r"^charts/export/$",views.ExportToCSV.as_view()),
    #generating control chart images
    url(r"^charts/control_chart.png$", views.ControlChartImage.as_view(), name="control_chart"),

    #performing qa
    url(r"^units/$", views.ChooseUnit.as_view(), name="choose_unit"),
    url(r"^(?P<frequency>[\w-]+)/$", views.UnitGroupedFrequencyListView.as_view(), name="qa_by_frequency"),
    url(r"^(?P<pk>\d+)$", views.PerformQAView.as_view(), name="perform_qa"),
    url(r"^(?P<frequency>[\w-]+)/unit/(?P<unit_number>\d+)/$", views.UnitFrequencyListView.as_view(), name="qa_by_frequency_unit"),

)