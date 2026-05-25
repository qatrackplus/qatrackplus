from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from qatrack.api.comments import views

router = routers.DefaultRouter()
router.register(r'comments', views.CommentViewSet)

urlpatterns = [
    re_path(r'^', include(router.urls)),
]
