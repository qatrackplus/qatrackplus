from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.views.generic.base import TemplateView

from django.contrib import admin
admin.autodiscover()

import settings

urlpatterns = patterns('',

    url(r'^$', TemplateView.as_view(template_name="homepage.html"), name="home"),

    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': settings.LOGIN_URL}),
    url(r'^accounts/details/$',TemplateView.as_view(template_name="registration/account.html"),name="account-details"),

    url(r'^accounts/', include('registration.urls')),

    url(r'^qa/', include('qatrack.qa.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^', include('genericdropdown.urls')),

)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^%s(?P<path>.*)$' % settings.MEDIA_URL[1:],
         'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    )
