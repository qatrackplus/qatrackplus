from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from qatrack.api.contenttypes import views

router = routers.DefaultRouter()
router.register(r'contenttypes', views.ContentTypeViewSet)

urlpatterns = [
    re_path(r'^', include(router.urls)),
]
