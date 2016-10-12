
from django.conf.urls import include, url

from qatrack.service_log import views

urlpatterns = [

    url(r"^$", views.SLDashboard.as_view(), name="sl_dash"),
    url(r'^create/$', views.CreateServiceEvent.as_view(), name="sl_new"),
    url(r'^edit/(?P<pk>\d+)/$', views.UpdateServiceEvent.as_view(), name="sl_edit"),
    url(r'^details/(?P<pk>\d+)/$', views.DetailsServiceEvent.as_view(), name="sl_details"),
    url(r'^all/$', views.ServiceEventsBaseList.as_view(), name="sl_list_all"),

    url(r'^unit_service_area/$', views.unit_service_areas, name="unit_service_areas")
]
