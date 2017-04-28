
from django.conf.urls import include, url

from qatrack.units import views

urlpatterns = [
    url(r"^vendors/$", views.VendorsList.as_view(), name="vendor_list"),
    url(r"^units/$", views.UnitList.as_view(), name="unit_list"),
]
