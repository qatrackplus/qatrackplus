from django.urls import re_path

from qatrack.qatrack_core import views

urlpatterns = [
    re_path(r"^comment/ajax_comment/$", views.ajax_comment, name='ajax_comment'),
]
