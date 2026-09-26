"""A Site domain that already carries a scheme must not get a second one.

Issue #853: report links were emitted as
``http://https://example.com/servicelog/...``. A browser reads that as host
"https" with the real host pushed into the path, so the link does not
resolve. Setting the Site domain to a full URL is a common configuration and
one this codebase already accommodates elsewhere.
"""
from django.contrib.sites.models import Site
from django.test import TestCase, override_settings

from qatrack.qatrack_core.utils import site_base_url


def set_domain(domain):
    site = Site.objects.get_current()
    site.domain = domain
    site.save()
    Site.objects.clear_cache()


@override_settings(HTTP_OR_HTTPS="http")
class TestSiteBaseUrl(TestCase):

    def test_bare_host_gets_the_configured_scheme(self):
        set_domain("example.com")
        assert site_base_url() == "http://example.com"

    def test_domain_with_https_scheme_is_left_alone(self):
        set_domain("https://example.com")
        assert site_base_url() == "https://example.com"

    def test_domain_with_http_scheme_is_left_alone(self):
        set_domain("http://example.com")
        assert site_base_url() == "http://example.com"

    def test_trailing_slash_is_dropped(self):
        set_domain("https://example.com/")
        assert site_base_url() == "https://example.com"

    def test_no_double_scheme_ever(self):
        for domain in ["example.com", "https://example.com", "http://example.com/"]:
            set_domain(domain)
            url = site_base_url()
            assert url.count("://") == 1, "%r produced %r" % (domain, url)


@override_settings(HTTP_OR_HTTPS="http")
class TestReportLinks(TestCase):
    """The reported symptom, at the level a user sees it."""

    def test_make_url_does_not_double_the_scheme(self):
        from qatrack.reports import reports

        set_domain("https://example.com")
        url = reports.BaseReport(report_opts={}).make_url(
            "/servicelog/event/details/826/", plain=True
        )
        assert url == "https://example.com/servicelog/event/details/826/", url

    def test_make_url_adds_a_scheme_to_a_bare_host(self):
        from qatrack.reports import reports

        set_domain("example.com")
        url = reports.BaseReport(report_opts={}).make_url("/reports/", plain=True)
        assert url == "http://example.com/reports/", url

    def test_report_url_does_not_double_the_scheme(self):
        from qatrack.reports import reports

        set_domain("https://example.com")
        url = reports.BaseReport(report_opts={}).get_report_url()
        assert url.startswith("https://example.com/"), url
        assert url.count("://") == 1, url
