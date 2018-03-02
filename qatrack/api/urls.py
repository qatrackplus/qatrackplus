from django.conf.urls import include, url
from rest_framework.authtoken import views
from rest_framework.schemas import get_schema_view

schema_view = get_schema_view(title='QATrack+ API')

urlpatterns = [
    url(r'^get-token/', views.obtain_auth_token, name="get-token"),
    url(r'^authorize/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^auth/', include('qatrack.api.auth.urls')),
    url(r'^contenttypes/', include('qatrack.api.contenttypes.urls')),
    url(r'^units/', include('qatrack.api.units.urls')),
    url(r'^qa/', include('qatrack.api.qa.urls')),
    url(r'^servicelog/', include('qatrack.api.service_log.urls')),
    url(r'^schema/$', schema_view),
]
