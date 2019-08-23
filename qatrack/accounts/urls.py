from django.conf.urls import include, url
from django.contrib.auth import views as auth_views

from qatrack.accounts import views

urlpatterns = [
    url(r'^logout/$', auth_views.LogoutView.as_view()),
    url(r'^details/$', views.AccountDetails.as_view(), name="account-details"),
    url(r'^register/$', views.RegisterView.as_view(), name="account-register"),
    url(r'^password/change/$', views.ChangePasswordView.as_view(), name="account-change-password"),
    url(
        r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.ResetPasswordConfirmView.as_view(),
        name='account-password-reset-confirm'
    ),
    url(r'^groups/$', views.GroupsApp.as_view(), name="groups-app"),
    url('^', include('django.contrib.auth.urls')),
    url(r'^', include('registration.backends.simple.urls')),
]
