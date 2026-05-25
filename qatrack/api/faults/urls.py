from django.urls import include
from django.urls import re_path as url
from rest_framework import routers

from qatrack.api.faults import views

router = routers.DefaultRouter()
router.register(r'faults', views.FaultViewSet)
router.register(r'faulttypes', views.FaultTypeViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
