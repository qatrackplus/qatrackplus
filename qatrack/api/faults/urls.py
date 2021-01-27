from django.conf.urls import include, url
from rest_framework import routers

from qatrack.api.faults import views

router = routers.DefaultRouter()
router.register(r'faults', views.FaultViewSet)
router.register(r'faulttypes', views.FaultTypeViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
