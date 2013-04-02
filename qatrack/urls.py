from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

import settings

urlpatterns = patterns('',

    url(r'^$', direct_to_template, {
        'template': "homepage.html",
        'extra_context': {},
        }, name='home'
        ),

    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': settings.LOGIN_URL}),

    url(r'^accounts/', include('registration.urls')),

    url(r'^qa/', include('qatrack.qa.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^', include('genericdropdown.urls')),

)
