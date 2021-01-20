from django.conf.urls import url

from qatrack.faults import views

urlpatterns = [
    url(r'^$', views.FaultList.as_view(), name='fault_list'),
    url(r'^review/choose-unit/$', views.ChooseUnitForViewFaults.as_view(), name="fault_choose_unit"),
    url(r'^unit/(?P<unit_number>[/\d]+)/$', views.FaultsByUnit.as_view(), name='fault_list_by_unit'),
    url(
        r'^unit/(?P<unit_number>[/\d]+)/type/(?P<slug>[\w-]+)/$',
        views.FaultsByUnitFaultType.as_view(),
        name='fault_list_by_unit_type',
    ),
    url(r'^type/$', views.FaultTypeList.as_view(), name='fault_type_list'),
    url(r'^type/autocomplete.json$', views.fault_type_autocomplete, name="fault_type_autocomplete"),
    url(r'^type/(?P<slug>[\w-]+)/$', views.FaultTypeDetails.as_view(), name='fault_type_details'),
    url(r'^(?P<pk>\d+)?/$', views.FaultDetails.as_view(), name='fault_details'),
    url(r'^create/$', views.CreateFault.as_view(), name='fault_create'),
    url(r'^create/ajax/$', views.fault_create_ajax, name='fault_create_ajax'),
    url(r'^edit/(?P<pk>\d+)?/$', views.EditFault.as_view(), name='fault_edit'),
]
