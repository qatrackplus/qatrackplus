from django.conf.urls import include
from django.urls import re_path
from rest_framework.authtoken import views as auth_views
from rest_framework.schemas import get_schema_view

from qatrack.api import views

schema_view = get_schema_view(title='QATrack+ API')


urlpatterns = [
    re_path(r'^$', views.all_api_roots, name="api-root"),
    re_path(r'^get-token/', auth_views.obtain_auth_token, name="get-token"),
    #    re_path(r'^authorize/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^attachments/', include('qatrack.api.attachments.urls')),
    re_path(r'^auth/', include('qatrack.api.auth.urls')),
    re_path(r'^comments/', include('qatrack.api.comments.urls')),
    re_path(r'^contenttypes/', include('qatrack.api.contenttypes.urls')),
    re_path(r'^faults/', include('qatrack.api.faults.urls')),
    re_path(r'^parts/', include('qatrack.api.parts.urls')),
    re_path(r'^qa/', include('qatrack.api.qa.urls')),
    re_path(r'^qc/', include('qatrack.api.qa.urls')),
    re_path(r'^servicelog/', include('qatrack.api.service_log.urls')),
    re_path(r'^units/', include('qatrack.api.units.urls')),
    re_path(r'^schema/$', schema_view),
]
