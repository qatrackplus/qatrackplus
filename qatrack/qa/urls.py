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

    url(r"^$", views.UTCList.as_view(),name="all_lists"),

    #view for composite calculations via ajax
    url(r"^composite/$", views.CompositeCalculation.as_view(), name="composite"),


    #api urls
    url(r"^api/",include(v1_api.urls)),

    #review utc's
    url(r"^review/$", views.UTCReview.as_view(), name="review_all"),
    url(r"^review/utc/(?P<pk>\d+)/$", views.UTCInstances.as_view(), name="review_utc"),
    url(r"^review/frequency/$", views.ChooseFrequencyForReview.as_view(), name="choose_review_frequency"),
    url(r"^review/frequency/(?P<frequency>[/\w-]+)/$", views.UTCFrequencyReview.as_view(), name="review_by_frequency"),
    url(r"^review/unit/$", views.ChooseUnitForReview.as_view(), name="choose_review_unit"),
    url(r"^review/unit/(?P<unit_number>[/\d]+)/$", views.UTCUnitReview.as_view(), name="review_by_unit"),

    #test list instances
    url(r"^review/tli/details/$", views.TestListInstances.as_view(), name="complete_instances"),
    url(r"^review/tli/details/(?P<pk>\d+)/$", views.ReviewTestListInstance.as_view(), name="review_test_list_instance"),
    url(r"^review/unreviewed/$", views.Unreviewed.as_view(), name="unreviewed"),


    url(r"^units/$", views.ChooseUnit.as_view(), name="choose_unit"),
    url(r"^perform/utc/(?P<pk>\d+)/$", views.PerformQA.as_view(), name="perform_qa"),
    url(r"^tli/in-progress/$", views.InProgress.as_view(), name="in_progress"),
    url(r"^tli/edit/(?P<pk>\d+)/$", views.EditTestListInstance.as_view(), name="edit_tli"),
    url(r"^(?P<frequency>[/\w-]+)/unit/(?P<unit_number>[/\d]+)/$", views.UnitFrequencyListView.as_view(), name="qa_by_frequency_unit"),
    url(r"^(?P<frequency>[/\w-]+)/$", views.FrequencyList.as_view(), name="qa_by_frequency"),


    url(r"charts/$", views.ChartView.as_view(), name="charts"),
    url(r"^charts/export/$",views.ExportToCSV.as_view()),
    url(r"^charts/control_chart.png$", views.ControlChartImage.as_view(), name="control_chart"),






)