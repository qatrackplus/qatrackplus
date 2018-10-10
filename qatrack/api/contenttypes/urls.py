from django.conf.urls import include, url
from rest_framework import routers

from qatrack.api.contenttypes import views

router = routers.DefaultRouter()
router.register(r'contenttypes', views.ContentTypeViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
