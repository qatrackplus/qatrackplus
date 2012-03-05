from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

import views

urlpatterns = patterns('',
    url(r"^validate/([\d+])/$", views.validate, name="validate"),
)