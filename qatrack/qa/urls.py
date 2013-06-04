from django.conf.urls.defaults import patterns, include, url

from views import base, perform, review, charts

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

    url(r"^(?P<data>data/)?$", base.UTCList.as_view(), name="all_lists"),

    # view for composite calculations via ajax
    url(r"^composite/$", perform.CompositeCalculation.as_view(), name="composite"),

    # view for uploads via ajax
    url(r"^upload/$", perform.Upload.as_view(), name="upload"),

    # api urls
    url(r"^api/", include(v1_api.urls)),

    url(r"^charts/$", can_view_history(charts.ChartView.as_view()), name="charts"),
    url(r"^charts/export/$", can_view_history(charts.ExportToCSV.as_view()), name="export_data"),
    url(r"^charts/data/$", can_view_history(charts.BasicChartData.as_view()), name="chart_data"),
    url(r"^charts/control_chart.png$", can_view_history(charts.ControlChartImage.as_view()), name="control_chart"),

    # overall program status
    url(r"^review/$", can_view_history(review.Overview.as_view()), name="overview"),
    url(r"^review/due-dates/$", can_view_history(review.DueDateOverview.as_view()), name="overview_due_dates"),

    # review utc's
    url(r"^review/all/(?P<data>data/)?$", can_edit(review.UTCReview.as_view()), name="review_all"),
    url(r"^review/utc/(?P<pk>\d+)/(?P<data>data/)?$", can_edit(review.UTCInstances.as_view()), name="review_utc"),
    url(r"^review/frequency/$", can_edit(review.ChooseFrequencyForReview.as_view()), name="choose_review_frequency"),
    url(r"^review/frequency/(?P<frequency>[/\w-]+?)/(?P<data>data/)?$", can_edit(review.UTCFrequencyReview.as_view()), name="review_by_frequency"),
    url(r"^review/unit/$", can_edit(review.ChooseUnitForReview.as_view()), name="choose_review_unit"),
    url(r"^review/unit/(?P<unit_number>[/\d]+)/(?P<data>data/)?$", can_edit(review.UTCUnitReview.as_view()), name="review_by_unit"),

    # test list instances
    url(r"^session/details/(?P<data>data/)?$", can_edit(base.TestListInstances.as_view()), name="complete_instances"),
    url(r"^session/details/(?P<pk>\d+)/$", can_edit(review.ReviewTestListInstance.as_view()), name="review_test_list_instance"),
    url(r"^session/unreviewed/(?P<data>data/)?$", can_view_history(review.Unreviewed.as_view()), name="unreviewed"),
    url(r"^session/in-progress/(?P<data>data/)?$", perform.InProgress.as_view(), name="in_progress"),
    url(r"^session/edit/(?P<pk>\d+)/$", perform.EditTestListInstance.as_view(), name="edit_tli"),


    url(r"^unit/$", perform.ChooseUnit.as_view(), name="choose_unit"),
    url(r"^utc/perform/(?P<pk>\d+)/$", perform.PerformQA.as_view(), name="perform_qa"),
    url(r"^utc/perform/info/(?P<unit>\d+)/(?P<test_list>\d+)/$", perform.PerformQAInfo.as_view(), name="perform_qa_info"),

    url(r"^unit/(?P<unit_number>[/\d]+)/frequency/(?P<frequency>[/\w-]+?)/(?P<data>data/)?$", perform.UnitFrequencyList.as_view(), name="qa_by_frequency_unit"),
    url(r"^unit/(?P<unit_number>[/\d]+)/(?P<data>data/)?$", perform.UnitList.as_view(), name="qa_by_unit"),

    url(r"^frequency/(?P<frequency>[/\w-]+)/unit/(?P<unit_number>[/\d]+)/(?P<data>data/)?$", perform.UnitFrequencyList.as_view(), name="qa_by_unit_frequency"),
    url(r"^frequency/(?P<frequency>[/\w-]+?)/(?P<data>data/)?$", perform.FrequencyList.as_view(), name="qa_by_frequency"),

)
