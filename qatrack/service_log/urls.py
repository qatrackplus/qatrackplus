
from django.conf.urls import patterns, include, url

import views

urlpatterns = patterns(

    '',
    url(r"^$", views.SLDashboard.as_view(), name="sl_dash"),
    url(r'^create/$', views.CreateServiceEvent.as_view(), name="sl_new"),
    url(r'^edit/(?P<pk>\d+)/$', views.UpdateServiceEvent.as_view(), name="sl_edit"),

    url(r'^unit_service_area/$', views.unit_service_areas, name="unit_service_areas")
)
