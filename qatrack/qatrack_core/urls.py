from django.urls import re_path as url

from qatrack.qatrack_core import views

urlpatterns = [
    url(r"^comment/ajax_comment/$", views.ajax_comment, name='ajax_comment'),
]
