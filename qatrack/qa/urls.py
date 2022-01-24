from django.conf.urls import url

import qatrack.qa.views.admin

from .views import admin, base, charts, perform, review

urlpatterns = [
    # CUSTOM ADMIN PAGES
    # Copy references and tolerances between testlists
    url(
        r'^admin/copy_refs_and_tols/$',
        admin.CopyReferencesAndTolerances(admin.CopyReferencesAndTolerancesForm),
        name="qa_copy_refs_and_tols"
    ),
    url(
        r'^admin/copy_refs_and_tols/gettestlists/(?P<source_unit>[:|\w]+)/(?P<content_type>[:|\w]+)/$',
        qatrack.qa.views.admin.testlist_json,
        name='qa_copy_refs_and_tols_testlist_json'
    ),
    url(r'^admin/export_testpack/$', admin.ExportTestPack.as_view(), name="qa_export_testpack"),
    url(r'^admin/import_testpack/$', admin.ImportTestPack.as_view(), name="qa_import_testpack"),
    url(r'^admin/recurrences/$', admin.recurrence_examples, name="qa_recurrences"),
    url(r"^$", base.UTCList.as_view(), name="all_lists"),

    # view for composite calculations via ajax
    url(r"^composite/$", perform.CompositeCalculation.as_view(), name="composite"),
    url(r"^autosave/$", perform.autosave, name="autosave"),
    url(r"^autosave/load/$", perform.autosave_load, name="autosave_load"),

    # view for uploads via ajax
    url(r"^upload/$", perform.Upload.as_view(), name="upload"),
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
    url(r"^review/due-dates-user/$", review.DueDateOverviewUser.as_view(), name="overview_due_dates_user"),

    # review utc's
    url(r"^review/all/$", review.UTCReview.as_view(), name="review_all"),
    url(r"^review/yourall/$", review.UTCYourReview.as_view(), name="review_your_all"),
    url(r"^review/utc/(?P<pk>\d+)/$", review.UTCInstances.as_view(), name="review_utc"),
    url(r"^review/frequency/$", review.ChooseFrequencyForReview.as_view(), name="choose_review_frequency"),
    url(
        r"^review/frequency/(?P<frequency>[/\w-]+?)/$", review.UTCFrequencyReview.as_view(), name="review_by_frequency"
    ),
    url(r"^review/unit/$", review.ChooseUnitForReview.as_view(), name="choose_review_unit"),
    url(r"^review/unit/(?P<unit_number>[/\d]+)/$", review.UTCUnitReview.as_view(), name="review_by_unit"),
    url(r"^review/inactive/$", review.InactiveReview.as_view(), name="review_inactive"),
    url(r"^review/yourinactive/$", review.YourInactiveReview.as_view(), name="review_your_inactive"),

    # test list instances
    url(r"^session/details/$", base.TestListInstances.as_view(), name="complete_instances"),
    url(
        r"^session/details(?:/(?P<pk>\d+))?/report/$",
        review.test_list_instance_report,
        name="test_list_instance_report"
    ),
    url(
        r"^session/details(?:/(?P<pk>\d+))?/$",
        review.TestListInstanceDetails.as_view(),
        name="view_test_list_instance"
    ),
    url(
        r"^session/delete(?:/(?P<pk>\d+))?/$",
        review.TestListInstanceDelete.as_view(),
        name="delete_test_list_instance"
    ),
    url(r"^session/review/$", review.Unreviewed.as_view(), name="unreviewed-alt"),
    url(
        r"^session/review(?:(?:/(?P<rtsqa_form>[a-zA-Z0-9-_]+))?(?:/(?P<pk>\d+)))?/$",
        review.ReviewTestListInstance.as_view(),
        name="review_test_list_instance"
    ),
    url(r"^session/review/bulk/$", review.bulk_review, name="qa-bulk-review"),
    url(r"^session/unreviewed/$", review.Unreviewed.as_view(), name="unreviewed"),
    url(r"^session/unreviewed/visible/$", review.UnreviewedVisibleTo.as_view(), name="unreviewed_visible_to"),
    url(r"^session/group/$", review.ChooseGroupVisibleTo.as_view(), name="choose_group_visible"),
    url(
        r"^session/unreviewedbygroup/(?P<group>[/\d]+)/$",
        review.UnreviewedByVisibleToGroup.as_view(),
        name="unreviewed_by_group"
    ),
    url(r"^session/in-progress/$", perform.InProgress.as_view(), name="in_progress"),
    url(r"^session/continue/(?P<pk>\d+)/$", perform.ContinueTestListInstance.as_view(), name="continue_tli"),
    url(r"^session/edit/(?P<pk>\d+)/$", perform.EditTestListInstance.as_view(), name="edit_tli"),
    url(r"^unit/$", perform.ChooseUnit.as_view(), name="choose_unit"),
    url(r"^utc/perform(?:/(?P<pk>\d+))?/$", perform.PerformQA.as_view(), name="perform_qa"),
    url(r"^site/(?P<site>[/\w-]+?)/$", perform.SiteList.as_view(), name="qa_by_site"),
    url(
        r"^unit/(?P<unit_number>[/\d]+)/frequency/(?P<frequency>[/\w-]+?)/$",
        perform.UnitFrequencyList.as_view(),
        name="qa_by_frequency_unit"
    ),
    url(r"^unit/(?P<unit_number>[/\d]+)/$", perform.UnitList.as_view(), name="qa_by_unit"),
    url(
        r"^frequency/(?P<frequency>[/\w-]+)/unit/(?P<unit_number>[/\d]+)/$",
        perform.UnitFrequencyList.as_view(),
        name="qa_by_unit_frequency"
    ),
    url(r"^frequency/(?P<frequency>[/\w-]+?)/$", perform.FrequencyList.as_view(), name="qa_by_frequency"),
    url(r"^tree/category/$", perform.CategoryTree.as_view(), name="qa_category_tree"),
    url(r"^tree/frequency/$", perform.FrequencyTree.as_view(), name="qa_frequency_tree"),
    url(
        r"^category/(?P<category>[/\w-]+)/unit/(?P<unit_number>[/\d]+)/$",
        perform.UnitCategoryList.as_view(),
        name="qa_by_unit_category"
    ),
    url(r"^category/(?P<category>[/\w-]+?)/$", perform.CategoryList.as_view(), name="qa_by_category"),
    url(r"^due-and-overdue/$", perform.DueAndOverdue.as_view(), name="qa_by_overdue"),

    # search urls
    url(r"^searcher/test/$", base.test_searcher, name='test_searcher'),
    url(r"^searcher/tolerance/$", base.tolerance_searcher, name='tolerance_searcher'),
    url(r"^searcher/test_list/$", base.test_list_searcher, name='test_list_searcher'),
    url(r"^searcher/test_list_cycle/$", base.test_list_cycle_searcher, name='test_list_cycle_searcher'),
    url(r"^searcher/test_instance/$", base.test_instance_searcher, name='test_instance_searcher'),
    url(r"^searcher/test_list_instance/$", base.test_list_instance_searcher, name='test_list_instance_searcher'),
]
