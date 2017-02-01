
from django.conf.urls import include, url

from qatrack.service_log import views

urlpatterns = [

    url(r"^$", views.SLDashboard.as_view(), name="sl_dash"),
    url(r'^create/$', views.CreateServiceEvent.as_view(), name="sl_new"),
    url(r'^edit(?:/(?P<pk>\d+))?/$', views.UpdateServiceEvent.as_view(), name="sl_edit"),
    url(r'^details(?:/(?P<pk>\d+))?/$', views.DetailsServiceEvent.as_view(), name="sl_details"),
    url(r'^se/(?P<f>\S+)?$', views.ServiceEventsBaseList.as_view(), name="sl_list_all"),
    url(r'^qaf/(?P<f>\S+)?$', views.QAFollowupsBaseList.as_view(), name="qaf_list_all"),
    url(r'^se_searcher/$', views.se_searcher, name="se_searcher"),
    url(r'^tli_select(?:/(?P<pk>\d+))?(?:/(?P<form>[a-zA-Z0-9-_]+)/)?$', views.TLISelect.as_view(), name="tli_select"),
    url(r'^tli_statuses/$', views.tli_statuses, name="tli_statuses"),
    url(r'^unit_sa_utc/$', views.unit_sa_utc, name="unit_sa_utc")
]
