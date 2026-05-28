from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from qatrack.api.faults import views

router = routers.DefaultRouter()
router.register(r'faults', views.FaultViewSet)
router.register(r'faulttypes', views.FaultTypeViewSet)

urlpatterns = [
    re_path(r'^', include(router.urls)),
]
