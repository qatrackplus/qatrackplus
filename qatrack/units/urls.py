
from django.conf.urls import include, url

from qatrack.units import views

urlpatterns = [
    url(r"^unit_available_time(?:/(?P<pk>\d+))?/$", views.UnitAvailableTimeChange.as_view(), name="unit_available_time"),
    url(r'^handle_unit_available_time/$', views.handle_unit_available_time, name='handle_unit_available_time'),
    url(r'^handle_unit_available_time_edit/$', views.handle_unit_available_time_edit, name='handle_unit_available_time_edit'),
    url(r'^get_unit_available_time_data/$', views.get_unit_available_time_data, name='get_unit_available_time_data'),
]
