from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.templatetags.staticfiles import \
    static as static_url
from django.views.generic.base import RedirectView

from model_report import report
from qatrack.qatrack_core.views import homepage

admin.autodiscover()

report.autodiscover()


favicon_view = RedirectView.as_view(url=static_url("qatrack_core/img/favicon.ico"), permanent=True)
touch_view = RedirectView.as_view(url=static_url("qatrack_core/img/apple-touch-icon.png"), permanent=True)


class QAToQC(RedirectView):

    permanent = True
    query_string = True

    def get_redirect_url(self, *args, **kwargs):
        return "/qc/%s" % kwargs['terms']


urlpatterns = [
    url(r'^$', homepage, name="home"),
    url(r'^accounts/', include('qatrack.accounts.urls')),
    url(r'^qa/(?P<terms>.*)$', QAToQC.as_view()),
    url(r'^qc/', include('qatrack.qa.urls')),
    url(r'^units/', include('qatrack.units.urls')),
    url(r'^core/', include('qatrack.qatrack_core.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^favicon\.ico$', favicon_view),
    url(r'^apple-touch-icon\.png$', touch_view),

    # third party
    url(r'^', include('genericdropdown.urls')),
    url(r'^comments/', include('django_comments.urls')),
    url(r'^admin/dynamic_raw_id/', include('dynamic_raw_id.urls')),
    url(r'^api/', include('qatrack.api.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.USE_SERVICE_LOG:
    urlpatterns += [url(r'^servicelog/', include('qatrack.service_log.urls'))]

if settings.USE_PARTS:
    urlpatterns += [url(r'^parts/', include('qatrack.parts.urls'))]

if settings.USE_ISSUES:
    urlpatterns += [url(r'^issues/', include('qatrack.issue_tracker.urls'))]

if settings.USE_SQL_REPORTS:
    urlpatterns += [url(r'^reports/', include('explorer.urls'))]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
