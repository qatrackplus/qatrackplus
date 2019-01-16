from django.conf import settings
from django.conf.urls import include, url
from django.contrib.auth.views import logout

from . import views

urlpatterns = [
    url(r'^logout/$', logout, {'next_page': settings.LOGIN_URL}),
    url(r'^details/$', views.AccountDetails.as_view(), name="account-details"),
    url(r'^groups/$', views.GroupsApp.as_view(), name="groups-app"),
    url('^', include('django.contrib.auth.urls')),
    url(r'^', include('registration.backends.simple.urls')),
]
