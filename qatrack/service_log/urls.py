from django.conf.urls import url

from qatrack.service_log import views

urlpatterns = [
    url(r"^$", views.SLDashboard.as_view(), name="sl_dash"),
    url(r'^event/$', views.ServiceEventsBaseList.as_view(), name="sl_list_all"),
    url(r'^event/create/$', views.CreateServiceEvent.as_view(), name='sl_new'),
    url(r'^event/create/choose-unit/$', views.ChooseUnitForNewSE.as_view(), name="sl_unit_new"),
    url(r'^event/edit(?:/(?P<pk>\d+))?/$', views.UpdateServiceEvent.as_view(), name="sl_edit"),
    url(r'^event/details(?:/(?P<pk>\d+))?/$', views.DetailsServiceEvent.as_view(), name="sl_details"),
    url(r'^event/delete(?:/(?P<pk>\d+))?/$', views.DeleteServiceEvent.as_view(), name='se_delete'),
    url(r'^event/review-required/$', views.ServiceEventsReviewRequiredList.as_view(), name="sl_list_review_required"),
    url(r'^event/review/choose-unit/$', views.ChooseUnitForViewSE.as_view(), name="sl_unit_view_se"),
    url(r'^event/unit/(?P<unit_number>\d+)/$', views.ServiceEventsByUnitList.as_view(), name="sl_list_by_unit"),
    url(r'^event/initiated-by/(?P<tli_pk>\d+)/$', views.ServiceEventsInitiatedByList.as_view(), name="sl_list_initiated_by"),
    url(r'^event/return-to-service-for/(?P<tli_pk>\d+)/$', views.ServiceEventsReturnToServiceForList.as_view(), name="sl_list_return_to_service_for"),
    url(r'^event/status/(?P<pk>\d+)/$', views.ServiceEventsByStatusList.as_view(), name="sl_list_by_status"),
    url(r'^event/report/(?P<pk>\d+)/$', views.service_log_report, name="sl_service_event_report"),
    url(r'^rtsqa/$', views.ReturnToServiceQABaseList.as_view(), name="rtsqa_list_all"),
    url(r'^rtsqa/incomplete/$', views.ReturnToServiceQAIncompleteList.as_view(), name="rtsqa_list_incomplete"),
    url(r'^rtsqa/unreviewed/$', views.ReturnToServiceQAUnreviewedList.as_view(), name="rtsqa_list_unreviewed"),
    url(r'^rtsqa/event/(?P<se_pk>\d+)$', views.ReturnToServiceQAForEventList.as_view(), name="rtsqa_list_for_event"),
    url(r'^se-searcher/$', views.se_searcher, name="se_searcher"),
    url(r'^tli-select(?:/(?P<pk>\d+))?(?:/(?P<form>[a-zA-Z0-9-_]+)/)?$', views.TLISelect.as_view(), name="tli_select"),
    url(r'^tli-statuses/$', views.tli_statuses, name="tli_statuses"),
    url(r'^unit-sa_utc/$', views.unit_sa_utc, name="unit_sa_utc"),
    url(r'^err/$', views.ErrorView.as_view(), name='err'),
    url(r'^down-time/$', views.ServiceEventDownTimesList.as_view(), name='se_down_time'),
    url(r'^handle-unit-down-time/$', views.handle_unit_down_time, name='handle_unit_down_time'),
]
