from django.urls import re_path
from qatrack.issue_tracker import views

urlpatterns = [
    re_path(r'^issue/new/$', views.IssueCreate.as_view(), name='issue_new'),
    re_path(r'^issue/details/(?P<pk>\d+)?$', views.IssueDetails.as_view(), name='issue_details'),
    re_path(r'^issues/$', views.IssueList.as_view(), name='issue_list'),
]
