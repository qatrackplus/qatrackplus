from django.urls import include
from django.urls import re_path as url
from rest_framework import routers

from qatrack.api.comments import views

router = routers.DefaultRouter()
router.register(r'comments', views.CommentViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
