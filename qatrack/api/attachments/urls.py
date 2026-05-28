from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from qatrack.api.attachments import views

router = routers.DefaultRouter()
router.register(r'attachments', views.AttachmentViewSet)

urlpatterns = [
    re_path(r'^', include(router.urls)),
]
