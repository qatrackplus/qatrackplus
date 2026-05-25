from django.urls import include
from django.urls import re_path as url
from rest_framework import routers

from qatrack.api.auth import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
