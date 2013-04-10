from django.conf.urls.defaults import patterns, include, url

import views
from qatrack.decorators import custom_permission_required as cpr
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
    api.GroupResource(),
]
for resource in resources:
    v1_api.register(resource)

can_view_history = cpr("qa.can_view_history")
can_edit = cpr("qa.change_testinstance") 

urlpatterns = patterns('',

                       url(r"^(?P<data>data/)?$", views.UTCList.as_view(), name="all_lists"),

                       # view for composite calculations via ajax
                       url(r"^composite/$", views.CompositeCalculation.as_view(), name="composite"),


                       # api urls
                       url(r"^api/", include(v1_api.urls)),

                       url(r"^charts/$", can_view_history(views.ChartView.as_view()), name="charts"),
                       url(r"^charts/export/$", can_view_history(views.ExportToCSV.as_view()), name="export_data"),
                       url(r"^charts/data/$", can_view_history(views.BasicChartData.as_view()), name="chart_data"),
                       # generating control chart images
                       url(r"^charts/control_chart.png$", can_view_history(views.ControlChartImage.as_view()), name="control_chart"),

                       # overall program status
                       url(r"^review/$", can_view_history(views.Overview.as_view()), name="overview"),
                       url(r"^review/due-dates/$", can_view_history(views.DueDateOverview.as_view()), name="overview_due_dates"),

                       # review utc's
                       url(r"^review/all/(?P<data>data/)?$", can_edit(views.UTCReview.as_view()), name="review_all"),
                       url(r"^review/utc/(?P<pk>\d+)/(?P<data>data/)?$", can_edit(views.UTCInstances.as_view()), name="review_utc"),
                       url(r"^review/frequency/$", can_edit(views.ChooseFrequencyForReview.as_view()), name="choose_review_frequency"),
                       url(r"^review/frequency/(?P<frequency>[/\w-]+?)/(?P<data>data/)?$", can_edit(views.UTCFrequencyReview.as_view()), name="review_by_frequency"),
                       url(r"^review/unit/$", can_edit(views.ChooseUnitForReview.as_view()), name="choose_review_unit"),
                       url(r"^review/unit/(?P<unit_number>[/\d]+)/(?P<data>data/)?$", can_edit(views.UTCUnitReview.as_view()), name="review_by_unit"),

                       # test list instances
                       url(r"^session/details/(?P<data>data/)?$", can_edit(views.TestListInstances.as_view()), name="complete_instances"),
                       url(r"^session/details/(?P<pk>\d+)/$", can_edit(views.ReviewTestListInstance.as_view()), name="review_test_list_instance"),
                       url(r"^session/unreviewed/(?P<data>data/)?$", can_view_history(views.Unreviewed.as_view()), name="unreviewed"),
                       url(r"^session/in-progress/(?P<data>data/)?$", views.InProgress.as_view(), name="in_progress"),
                       url(r"^session/edit/(?P<pk>\d+)/$", can_edit(views.EditTestListInstance.as_view()), name="edit_tli"),


                       url(r"^unit/$", views.ChooseUnit.as_view(), name="choose_unit"),
                       url(r"^utc/perform/(?P<pk>\d+)/$", views.PerformQA.as_view(), name="perform_qa"),

                       url(r"^unit/(?P<unit_number>[/\d]+)/frequency/(?P<frequency>[/\w-]+?)/(?P<data>data/)?$", views.UnitFrequencyList.as_view(), name="qa_by_frequency_unit"),
                       url(r"^unit/(?P<unit_number>[/\d]+)/(?P<data>data/)?$", views.UnitList.as_view(), name="qa_by_unit"),

                       url(r"^frequency/(?P<frequency>[/\w-]+)/unit/(?P<unit_number>[/\d]+)/(?P<data>data/)?$", views.UnitFrequencyList.as_view(), name="qa_by_unit_frequency"),
                       url(r"^frequency/(?P<frequency>[/\w-]+?)/(?P<data>data/)?$", views.FrequencyList.as_view(), name="qa_by_frequency"),

                       )
