from django.conf.urls import include, url
from rest_framework.authtoken import views as auth_views
from rest_framework.schemas import get_schema_view

from qatrack.api import views

schema_view = get_schema_view(title='QATrack+ API')


urlpatterns = [
    url(r'^$', views.all_api_roots, name="api-root"),
    url(r'^get-token/', auth_views.obtain_auth_token, name="get-token"),
    #    url(r'^authorize/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^attachments/', include('qatrack.api.attachments.urls')),
    url(r'^auth/', include('qatrack.api.auth.urls')),
    url(r'^comments/', include('qatrack.api.comments.urls')),
    url(r'^contenttypes/', include('qatrack.api.contenttypes.urls')),
    url(r'^faults/', include('qatrack.api.faults.urls')),
    url(r'^parts/', include('qatrack.api.parts.urls')),
    url(r'^qa/', include('qatrack.api.qa.urls')),
    url(r'^qc/', include('qatrack.api.qa.urls')),
    url(r'^servicelog/', include('qatrack.api.service_log.urls')),
    url(r'^units/', include('qatrack.api.units.urls')),
    url(r'^schema/$', schema_view),
]
