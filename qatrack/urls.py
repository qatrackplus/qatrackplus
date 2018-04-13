from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.templatetags.staticfiles import \
    static as static_url
from django.views.generic.base import RedirectView, TemplateView

admin.autodiscover()


favicon_view = RedirectView.as_view(url=static_url("qatrack_core/img/favicon.ico"), permanent=True)
touch_view = RedirectView.as_view(url=static_url("qatrack_core/img/apple-touch-icon.png"), permanent=True)

urlpatterns = [

    url(r'^$', TemplateView.as_view(template_name="homepage.html"), name="home"),

    url(r'^accounts/', include('qatrack.accounts.urls')),
    url(r'^qa/', include('qatrack.qa.urls')),
    url(r'^servicelog/', include('qatrack.service_log.urls')),
    url(r'^parts/', include('qatrack.parts.urls')),
    url(r'^units/', include('qatrack.units.urls')),
    url(r'^issues/', include('qatrack.issue_tracker.urls')),
    url(r'^core/', include('qatrack.qatrack_core.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^favicon\.ico$', favicon_view),
    url(r'^apple-touch-icon\.png$', touch_view),

    url(r'^', include('genericdropdown.urls')),
    url(r'^comments/', include('django_comments.urls')),

    url(r'^api/', include('qatrack.api.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
