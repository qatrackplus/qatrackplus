from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.templatetags.static import static as static_url
from django.urls import path
from django.views.generic.base import RedirectView
from django.views.i18n import JavaScriptCatalog

from qatrack.qatrack_core import views

admin.autodiscover()


favicon_view = RedirectView.as_view(url=static_url("qatrack_core/img/favicon.ico"), permanent=True)
touch_view = RedirectView.as_view(url=static_url("qatrack_core/img/apple-touch-icon.png"), permanent=True)


class QAToQC(RedirectView):

    permanent = True
    query_string = True

    def get_redirect_url(self, *args, **kwargs):
        return "/qc/%s" % kwargs['terms']


urlpatterns = [
    url(r'^$', views.homepage, name="home"),
    url(r'^400/$', views.handle_400, name="400"),
    url(r'^403/$', views.handle_403, name="403"),
    url(r'^404/$', views.handle_404, name="404"),
    url(r'^500/$', views.handle_500, name="500"),
    url(r'^accounts/', include('qatrack.accounts.urls')),
    url(r'^qa/(?P<terms>.*)$', QAToQC.as_view()),
    url(r'^qc/', include('qatrack.qa.urls')),
    url(r'^units/', include('qatrack.units.urls')),
    url(r'^core/', include('qatrack.qatrack_core.urls')),
    url(r'^servicelog/', include('qatrack.service_log.urls')),
    url(r'^parts/', include('qatrack.parts.urls')),
    url(r'^issues/', include('qatrack.issue_tracker.urls')),

    # Uncomment the next line to enable the admin:
    path(r'admin/', admin.site.urls),
    url(r'^favicon\.ico$', favicon_view),
    url(r'^apple-touch-icon\.png$', touch_view),

    # third party
    url(r'^', include('genericdropdown.urls')),
    url(r'^comments/', include('django_comments.urls')),
    url(r'^admin/dynamic_raw_id/', include('dynamic_raw_id.urls')),
    url(r'^api/', include('qatrack.api.urls')),
]

js_info_dict = {
    'packages': ('recurrence', ),
}
urlpatterns += [url(r'^jsi18n/$', JavaScriptCatalog.as_view(), js_info_dict)]

if settings.USE_SQL_REPORTS:
    urlpatterns.append(url(r'^reports/', include('explorer.urls')),)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# error handling views
handler400 = 'qatrack.qatrack_core.views.handle_400'
handler403 = 'qatrack.qatrack_core.views.handle_403'
handler404 = 'qatrack.qatrack_core.views.handle_404'
handler500 = 'qatrack.qatrack_core.views.handle_500'

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
