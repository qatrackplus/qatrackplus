from django.conf.urls import url

from qatrack.interlocks import views

urlpatterns = [
    url(r'^$', views.InterlockList.as_view(), name='interlock_list'),
    url(r'^(?P<pk>\d+)?/$', views.InterlockDetails.as_view(), name='interlock_details'),
    url(r'^edit/(?P<pk>\d+)?/$', views.EditInterlock.as_view(), name='interlock_edit'),
]
