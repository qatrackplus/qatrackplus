from django.conf.urls import url
from qatrack.issue_tracker import views

urlpatterns = [
    url(r'^issue/new/$', views.IssueCreate.as_view(), name='issue_new'),
    url(r'^issue/details/(?P<pk>\d+)?$', views.IssueDetails.as_view(), name='issue_details'),
    url(r'^issues/$', views.IssueList.as_view(), name='issue_list'),
]
