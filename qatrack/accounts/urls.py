from django.conf import settings
from django.conf.urls import include, url
from django.contrib.auth.views import (
    logout,
    password_reset_done,
    password_change_done
)
from . import views


urlpatterns = [
    url(r'^logout/$', logout, {'next_page': settings.LOGIN_URL}),
    url(r'^details/$', views.AccountDetails.as_view(), name="account-details"),
    url(r'^resetpassword/passwordsent/$', password_reset_done, name='password_reset_done'),
    url(r'^password-change-done/$', password_change_done, name='password_change_done'),
    url(r'^', include('registration.backends.simple.urls')),
]
