from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from qatrack.api.auth import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    re_path(r'^', include(router.urls)),
]
