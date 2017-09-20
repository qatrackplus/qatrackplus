from django.conf.urls import include, url
from .views import base, perform, review, charts, backup, admin, forms

from qatrack.qa import api
import qatrack.qa.views.admin
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


urlpatterns = [
    # CUSTOM ADMIN PAGES
    # Copy references and tolerances between testlists
    url(r'^admin/copy_refs_and_tols/$',
        admin.SetReferencesAndTolerances(forms.SetReferencesAndTolerancesForm), name="qa_copy_refs_and_tols"),
    url(r'^admin/copy_refs_and_tols/gettestlists/(?P<source_unit>[:|\w]+)/(?P<content_type>[:|\w]+)/$',
        qatrack.qa.views.admin.testlist_json, name='qa_copy_refs_and_tols_testlist_json'),


    url(r"^$", base.UTCList.as_view(), name="all_lists"),

    # view for composite calculations via ajax
    url(r"^composite/$", perform.CompositeCalculation.as_view(), name="composite"),

    # view for uploads via ajax
    url(r"^upload/$", perform.Upload.as_view(), name="upload"),

    # api urls
    url(r"^api/", include(v1_api.urls)),

    url(r"^charts/$", charts.ChartView.as_view(), name="charts"),
    url(r"^charts/export/csv/$", charts.ExportCSVView.as_view(), name="charts_export_csv"),
    url(r"^charts/data/$", charts.BasicChartData.as_view(), name="chart_data"),
    url(r"^charts/control_chart.png$", charts.ControlChartImage.as_view(), name="control_chart"),
    url(r"^charts/data/testlists/$", charts.get_test_lists_for_unit_frequencies, name="charts_testlists"),
    url(r"^charts/data/tests/$", charts.get_tests_for_test_lists, name="charts_tests"),


    # overall program status
    url(r"^review/$", review.Overview.as_view(), name="overview"),
    url(r"^review/overview-user/$", review.Overview.as_view(), name="overview_user"),
    url(r"^review/overview-objects/$", review.OverviewObjects.as_view(), name="overview_objects"),
    url(r"^review/due-dates/$", review.DueDateOverview.as_view(), name="overview_due_dates"),

    # review utc's
    url(r"^review/all/$", review.UTCReview.as_view(), name="review_all"),
    url(r"^review/yourall/$", review.UTCYourReview.as_view(), name="review_your_all"),
    url(r"^review/utc/(?P<pk>\d+)/$", review.UTCInstances.as_view(), name="review_utc"),
    url(r"^review/frequency/$", review.ChooseFrequencyForReview.as_view(), name="choose_review_frequency"),
    url(r"^review/frequency/(?P<frequency>[/\w-]+?)/$", review.UTCFrequencyReview.as_view(), name="review_by_frequency"),
    url(r"^review/unit/$", review.ChooseUnitForReview.as_view(), name="choose_review_unit"),
    url(r"^review/unit/(?P<unit_number>[/\d]+)/$", review.UTCUnitReview.as_view(), name="review_by_unit"),
    url(r"^review/inactive/$", review.InactiveReview.as_view(), name="review_inactive"),
    url(r"^review/yourinactive/$", review.YourInactiveReview.as_view(), name="review_your_inactive"),

    # test list instances
    url(r"^session/details/$", base.TestListInstances.as_view(), name="complete_instances"),
    url(r"^session/details(?:/(?P<pk>\d+))?/$", review.TestListInstanceDetails.as_view(), name="view_test_list_instance"),
    url(r"^session/review(?:/(?P<pk>\d+))?/$", review.ReviewTestListInstance.as_view(), name="review_test_list_instance"),
    url(r"^session/unreviewed/$", review.Unreviewed.as_view(), name="unreviewed"),
    url(r"^session/unreviewedvisible/$", review.UnreviewedVisibleTo.as_view(), name="unreviewed_visible_to"),

    url(r"^session/group/$", review.ChooseGroupVisibleTo.as_view(), name="choose_group_visible"),
    url(r"^session/unreviewedbygroup/(?P<group>[/\d]+)/$", review.UnreviewedByVisibleToGroup.as_view(), name="unreviewed_by_group"),

    url(r"^session/in-progress/$", perform.InProgress.as_view(), name="in_progress"),
    url(r"^session/continue/(?P<pk>\d+)/$", perform.ContinueTestListInstance.as_view(), name="continue_tli"),
    url(r"^session/edit/(?P<pk>\d+)/$", perform.EditTestListInstance.as_view(), name="edit_tli"),

    url(r"^unit/$", perform.ChooseUnit.as_view(), name="choose_unit"),
    url(r"^utc/perform(?:/(?P<pk>\d+))?/$", perform.PerformQA.as_view(), name="perform_qa"),

    url(r"^unit/(?P<unit_number>[/\d]+)/frequency/(?P<frequency>[/\w-]+?)/$", perform.UnitFrequencyList.as_view(), name="qa_by_frequency_unit"),
    url(r"^unit/(?P<unit_number>[/\d]+)/$", perform.UnitList.as_view(), name="qa_by_unit"),

    url(r"^frequency/(?P<frequency>[/\w-]+)/unit/(?P<unit_number>[/\d]+)/$", perform.UnitFrequencyList.as_view(), name="qa_by_unit_frequency"),
    url(r"^frequency/(?P<frequency>[/\w-]+?)/$", perform.FrequencyList.as_view(), name="qa_by_frequency"),


    url(r"^backup/$", backup.PaperFormRequest.as_view(), name="qa_paper_forms_request"),
    url(r"^backup/paper/$", backup.PaperForms.as_view(), name="qa_paper_forms"),

    url(r"^searcher/test/$", api.test_searcher, name='test_searcher'),
    url(r"^searcher/test_list/$", api.test_list_searcher, name='test_list_searcher'),
    url(r"^searcher/test_list_cycle/$", api.test_list_cycle_searcher, name='test_list_cycle_searcher'),
    url(r"^searcher/test_instance/$", api.test_instance_searcher, name='test_instance_searcher'),
    url(r"^searcher/test_list_instance/$", api.test_list_instance_searcher, name='test_list_instance_searcher'),

]


