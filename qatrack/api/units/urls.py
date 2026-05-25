from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from qatrack.api.units import views

router = routers.DefaultRouter()
router.register(r'units', views.UnitViewSet)
router.register(r'vendors', views.VendorViewSet)
router.register(r'unitclasses', views.UnitClassViewSet)
router.register(r'unittypes', views.UnitTypeViewSet)
router.register(r'modalities', views.ModalityViewSet)
router.register(r'sites', views.SiteViewSet)
router.register(r'availabletimes', views.UnitAvailableTimeViewSet)
router.register(r'availabletimeedits', views.UnitAvailableTimeEditViewSet)

urlpatterns = [
    re_path(r'^', include(router.urls)),
]
