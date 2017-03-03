
from django.conf.urls import include, url

from qatrack.parts import views

urlpatterns = [
    url(r'^parts_searcher$', views.parts_searcher, name='parts_searcher'),
    url(r'^parts_storage_searcher$', views.parts_storage_searcher, name='parts_storage_searcher'),
    url(r'^parts/$', views.PartsList.as_view(), name='parts_list'),
    url(r'^parts/new/$', views.PartUpdateCreate.as_view(), name='part_new'),
]
