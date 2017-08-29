
from django.conf.urls import include, url

from qatrack.parts import views

urlpatterns = [
    url(r'^parts_searcher$', views.parts_searcher, name='parts_searcher'),
    url(r'^parts_storage_searcher$', views.parts_storage_searcher, name='parts_storage_searcher'),
    url(r'^room_location_searcher$', views.room_location_searcher, name='room_location_searcher'),
    url(r'^list(?:/(?P<f>\S+))?/$', views.PartsList.as_view(), name='parts_list'),
    url(r'^new/$', views.PartUpdateCreate.as_view(), name='part_new'),
    url(r'^edit/(?P<pk>\d+)?$', views.PartUpdateCreate.as_view(), name='part_edit'),
    url(r'^details/(?P<pk>\d+)?$', views.PartDetails.as_view(), name='part_details'),
    url(r'^suppliers/$', views.SuppliersList.as_view(), name='suppliers_list'),
    url(r'^parts_units_cost(?:/(?P<pk>\d+))?/$', views.PartsUnitsCost.as_view(), name='parts_units_cost'),
    url(r'^go_parts_units_cost/$', views.go_units_parts_cost, name='go_units_parts_cost'),
    url(r'^low_parts_pdf/$', views.low_parts_pdf, name='low_parts_pdf'),
]
