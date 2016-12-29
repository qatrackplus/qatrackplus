from django.conf import settings
from django.conf.urls import include, url
from django.contrib.auth.views import (
    logout,
)
from . import views


urlpatterns = [
    url(r'^logout/$', logout, {'next_page': settings.LOGIN_URL}),
    url(r'^details/$', views.AccountDetails.as_view(), name="account-details"),
    url('^', include('django.contrib.auth.urls')),
    url(r'^', include('registration.backends.simple.urls')),
]
