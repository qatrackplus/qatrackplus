from django.conf import settings
from django.conf.urls import patterns, include, url
import views


urlpatterns = patterns('',
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': settings.LOGIN_URL}),
    url(r'^details/$', views.AccountDetails.as_view(), name="account-details"),
    url(r'^resetpassword/passwordsent/$', 'django.contrib.auth.views.password_reset_done', name='password_reset_done'),
    url(r'^password-change-done/$', 'django.contrib.auth.views.password_change_done', name='password_change_done'),
    url(r'^', include('registration.backends.simple.urls')),
)
