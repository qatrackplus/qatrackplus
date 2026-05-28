from django.urls import re_path
import qatrack.qa.views.admin

from .views import admin, base, charts, perform, review

urlpatterns = [
    # CUSTOM ADMIN PAGES
    # Copy references and tolerances between testlists
    re_path(
        r'^admin/copy_refs_and_tols/$',
        admin.CopyReferencesAndTolerances(admin.CopyReferencesAndTolerancesForm),
        name="qa_copy_refs_and_tols"
    ),
    re_path(
        r'^admin/copy_refs_and_tols/gettestlists/(?P<source_unit>[:|\w]+)/(?P<content_type>[:|\w]+)/$',
        qatrack.qa.views.admin.testlist_json,
        name='qa_copy_refs_and_tols_testlist_json'
    ),
    re_path(r'^admin/export_testpack/$', admin.ExportTestPack.as_view(), name="qa_export_testpack"),
    re_path(r'^admin/import_testpack/$', admin.ImportTestPack.as_view(), name="qa_import_testpack"),
    re_path(r'^admin/recurrences/$', admin.recurrence_examples, name="qa_recurrences"),
    re_path(r"^$", base.UTCList.as_view(), name="all_lists"),

    # view for composite calculations via ajax
    re_path(r"^composite/$", perform.CompositeCalculation.as_view(), name="composite"),
    re_path(r"^autosave/$", perform.autosave, name="autosave"),
    re_path(r"^autosave/load/$", perform.autosave_load, name="autosave_load"),

    # view for uploads via ajax
    re_path(r"^upload/$", perform.Upload.as_view(), name="upload"),
    re_path(r"^charts/$", charts.ChartView.as_view(), name="charts"),
    re_path(r"^charts/export/csv/$", charts.ExportCSVView.as_view(), name="charts_export_csv"),
    re_path(r"^charts/data/$", charts.BasicChartData.as_view(), name="chart_data"),
    re_path(r"^charts/control_chart.png$", charts.ControlChartImage.as_view(), name="control_chart"),
    re_path(r"^charts/data/testlists/$", charts.get_test_lists_for_unit_frequencies, name="charts_testlists"),
    re_path(r"^charts/data/tests/$", charts.get_tests_for_test_lists, name="charts_tests"),

    # overall program status
    re_path(r"^review/$", review.Overview.as_view(), name="overview"),
    re_path(r"^review/overview-user/$", review.Overview.as_view(), name="overview_user"),
    re_path(r"^review/overview-objects/$", review.OverviewObjects.as_view(), name="overview_objects"),
    re_path(r"^review/due-dates/$", review.DueDateOverview.as_view(), name="overview_due_dates"),
    re_path(r"^review/due-dates-user/$", review.DueDateOverviewUser.as_view(), name="overview_due_dates_user"),

    # review utc's
    re_path(r"^review/all/$", review.UTCReview.as_view(), name="review_all"),
    re_path(r"^review/yourall/$", review.UTCYourReview.as_view(), name="review_your_all"),
    re_path(r"^review/utc/(?P<pk>\d+)/$", review.UTCInstances.as_view(), name="review_utc"),
    re_path(r"^review/frequency/$", review.ChooseFrequencyForReview.as_view(), name="choose_review_frequency"),
    re_path(
        r"^review/frequency/(?P<frequency>[/\w-]+?)/$", review.UTCFrequencyReview.as_view(), name="review_by_frequency"
    ),
    re_path(r"^review/unit/$", review.ChooseUnitForReview.as_view(), name="choose_review_unit"),
    re_path(r"^review/unit/(?P<unit_number>[/\d]+)/$", review.UTCUnitReview.as_view(), name="review_by_unit"),
    re_path(r"^review/inactive/$", review.InactiveReview.as_view(), name="review_inactive"),
    re_path(r"^review/yourinactive/$", review.YourInactiveReview.as_view(), name="review_your_inactive"),

    # test list instances
    re_path(r"^session/details/$", base.TestListInstances.as_view(), name="complete_instances"),
    re_path(
        r"^session/details(?:/(?P<pk>\d+))?/report/$",
        review.test_list_instance_report,
        name="test_list_instance_report"
    ),
    re_path(
        r"^session/details(?:/(?P<pk>\d+))?/$",
        review.TestListInstanceDetails.as_view(),
        name="view_test_list_instance"
    ),
    re_path(
        r"^session/delete(?:/(?P<pk>\d+))?/$",
        review.TestListInstanceDelete.as_view(),
        name="delete_test_list_instance"
    ),
    re_path(r"^session/review/$", review.Unreviewed.as_view(), name="unreviewed-alt"),
    re_path(
        r"^session/review(?:(?:/(?P<rtsqa_form>[a-zA-Z0-9-_]+))?(?:/(?P<pk>\d+)))?/$",
        review.ReviewTestListInstance.as_view(),
        name="review_test_list_instance"
    ),
    re_path(r"^session/review/bulk/$", review.bulk_review, name="qa-bulk-review"),
    re_path(r"^session/unreviewed/$", review.Unreviewed.as_view(), name="unreviewed"),
    re_path(r"^session/unreviewed/visible/$", review.UnreviewedVisibleTo.as_view(), name="unreviewed_visible_to"),
    re_path(r"^session/group/$", review.ChooseGroupVisibleTo.as_view(), name="choose_group_visible"),
    re_path(
        r"^session/unreviewedbygroup/(?P<group>[/\d]+)/$",
        review.UnreviewedByVisibleToGroup.as_view(),
        name="unreviewed_by_group"
    ),
    re_path(r"^session/in-progress/$", perform.InProgress.as_view(), name="in_progress"),
    re_path(r"^session/continue/(?P<pk>\d+)/$", perform.ContinueTestListInstance.as_view(), name="continue_tli"),
    re_path(r"^session/edit/(?P<pk>\d+)/$", perform.EditTestListInstance.as_view(), name="edit_tli"),
    re_path(r"^unit/$", perform.ChooseUnit.as_view(), name="choose_unit"),
    re_path(r"^utc/perform(?:/(?P<pk>\d+))?/$", perform.PerformQA.as_view(), name="perform_qa"),
    re_path(r"^site/(?P<site>[/\w-]+?)/$", perform.SiteList.as_view(), name="qa_by_site"),
    re_path(
        r"^unit/(?P<unit_number>[/\d]+)/frequency/(?P<frequency>[/\w-]+?)/$",
        perform.UnitFrequencyList.as_view(),
        name="qa_by_frequency_unit"
    ),
    re_path(r"^unit/(?P<unit_number>[/\d]+)/$", perform.UnitList.as_view(), name="qa_by_unit"),
    re_path(
        r"^frequency/(?P<frequency>[/\w-]+)/unit/(?P<unit_number>[/\d]+)/$",
        perform.UnitFrequencyList.as_view(),
        name="qa_by_unit_frequency"
    ),
    re_path(r"^frequency/(?P<frequency>[/\w-]+?)/$", perform.FrequencyList.as_view(), name="qa_by_frequency"),
    re_path(r"^tree/category/$", perform.CategoryTree.as_view(), name="qa_category_tree"),
    re_path(r"^tree/frequency/$", perform.FrequencyTree.as_view(), name="qa_frequency_tree"),
    re_path(
        r"^category/(?P<category>[/\w-]+)/unit/(?P<unit_number>[/\d]+)/$",
        perform.UnitCategoryList.as_view(),
        name="qa_by_unit_category"
    ),
    re_path(r"^category/(?P<category>[/\w-]+?)/$", perform.CategoryList.as_view(), name="qa_by_category"),
    re_path(r"^due-and-overdue/$", perform.DueAndOverdue.as_view(), name="qa_by_overdue"),
]
