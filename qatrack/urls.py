from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.views.generic.base import TemplateView

from django.contrib import admin
admin.autodiscover()

urlpatterns = [

    url(r'^$', TemplateView.as_view(template_name="homepage.html"), name="home"),

    url(r'^accounts/', include('qatrack.accounts.urls')),
    url(r'^qa/', include('qatrack.qa.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^', include('genericdropdown.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
