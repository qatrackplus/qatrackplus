from django.conf.urls import include, url
from django.contrib.auth import views as auth_views

from qatrack.accounts import views

urlpatterns = [
    url(r'^logout/$', auth_views.LogoutView.as_view()),
    url(r'^details/$', views.AccountDetails.as_view(), name="account-details"),
    url(r'^groups/$', views.GroupsApp.as_view(), name="groups-app"),
    url('^', include('django.contrib.auth.urls')),
    url(r'^', include('registration.backends.simple.urls')),
]
