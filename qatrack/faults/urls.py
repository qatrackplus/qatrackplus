from django.conf.urls import url

from qatrack.faults import views

urlpatterns = [
    url(r'^$', views.FaultList.as_view(), name='fault_list'),
    url(r'^(?P<pk>\d+)?/$', views.FaultDetails.as_view(), name='fault_details'),
    url(r'^edit/(?P<pk>\d+)?/$', views.EditFault.as_view(), name='fault_edit'),
]
