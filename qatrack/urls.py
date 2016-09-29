from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic.base import TemplateView

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    url(r'^$', TemplateView.as_view(template_name="homepage.html"), name="home"),

    url(r'^accounts/', include('qatrack.accounts.urls')),
    url(r'^qa/', include('qatrack.qa.urls')),
    url(r'^servicelog/', include('qatrack.service_log.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^', include('genericdropdown.urls')),

)
if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}))
# if settings.DEBUG:
#     urlpatterns += patterns(
#         '',
#         (
#             r'^%s(?P<path>.*)$' % settings.MEDIA_URL[1:],
#             'django.views.static.serve',
#             {
#                 'document_root': settings.MEDIA_ROOT,
#                 'show_indexes': True
#             }
#         )
#     )
