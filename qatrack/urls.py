from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic.base import TemplateView

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    url(r'^$', TemplateView.as_view(template_name="homepage.html"), name="home"),

    url(r'^accounts/', include('qatrack.accounts.urls')),
    url(r'^qa/', include('qatrack.qa.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^', include('genericdropdown.urls')),

)

for pattern in urlpatterns:
    print '---------------------'
    if hasattr(pattern, 'name'):
        print pattern.name
        # print pattern.callback.func_name
        # print dir(pattern.callback)
    else:
        # for pat in pattern:
        #     print '    ------------'
        #     print '\t' + str(pat)
        # print dir(pattern)
        for u in pattern.url_patterns:
            if hasattr(u, 'name'):
                print u.name
            else:
                for another in u.url_patterns:
                    if hasattr(another, 'name'):
                        print another.name
        # print pattern.url_patterns

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
