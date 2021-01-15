from django.conf import settings
from django.conf.urls import include, url
from django.contrib.auth import views as auth_views

from qatrack.accounts import views
from qatrack.qatrack_core.views import handle_404

urlpatterns = [
    url(r'^logout/$', auth_views.LogoutView.as_view(), name="auth_logout"),
    url(r'^details/$', views.AccountDetails.as_view(), name="account-details"),
    url(r'^password/change/$', views.ChangePasswordView.as_view(), name="account-change-password"),
    url(
        r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.ResetPasswordConfirmView.as_view(),
        name='account-password-reset-confirm'
    ),
    url(r'^groups/$', views.GroupsApp.as_view(), name="groups-app"),
]

if settings.ACCOUNTS_SELF_REGISTER:
    urlpatterns += [
        url(r'^register/$', views.RegisterView.as_view(), name="account-register"),
    ]
else:
    urlpatterns += [
        url(r'^register/$', handle_404, name="account-register"),
    ]

urlpatterns += [
    url('^', include('django.contrib.auth.urls')),
    url(r'^', include('registration.backends.simple.urls')),
]
