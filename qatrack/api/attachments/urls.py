from django.conf.urls import include, url
from rest_framework import routers

from qatrack.api.attachments import views

router = routers.DefaultRouter()
router.register(r'attachments', views.AttachmentViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
