from django.conf.urls import include, url
from rest_framework import routers

from qatrack.api.comments import views

router = routers.DefaultRouter()
router.register(r'comments', views.CommentViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
