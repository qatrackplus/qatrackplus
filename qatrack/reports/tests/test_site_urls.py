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


class SiteCacheCleanup:
    """Clear Django's Site cache after every test.

    set_domain() clears the cache before the assertions, but site_base_url()
    then caches the modified Site again. TestCase rolls back the database row
    and not the cache, so without this a later test reads this test's domain
    instead of the restored value - an order-dependent failure that only shows
    up in a full-suite run.
    """

    def setUp(self):
        super().setUp()
        self.addCleanup(Site.objects.clear_cache)


@override_settings(HTTP_OR_HTTPS="http")
class TestSiteBaseUrl(SiteCacheCleanup, TestCase):

    def test_bare_host_gets_the_configured_scheme(self):
        set_domain("example.com")
        assert site_base_url() == "http://example.com"

    def test_domain_with_https_scheme_is_left_alone(self):
        set_domain("https://example.com")
        assert site_base_url() == "https://example.com"

    def test_domain_with_http_scheme_is_left_alone(self):
        set_domain("http://example.com")
        assert site_base_url() == "http://example.com"

    def test_uppercase_scheme_is_recognised_and_left_alone(self):
        """URI schemes are case-insensitive (RFC 3986)."""
        set_domain("HTTPS://example.com")
        assert site_base_url() == "HTTPS://example.com"

    def test_mixed_case_scheme_is_recognised(self):
        set_domain("Http://example.com")
        assert site_base_url() == "Http://example.com"

    def test_trailing_slash_is_dropped(self):
        set_domain("https://example.com/")
        assert site_base_url() == "https://example.com"

    def test_host_and_path_gets_one_scheme_and_is_otherwise_untouched(self):
        """A deployment was found with a host+path domain, e.g. "HOST/appname".

        That is not what Site.domain is for - Django documents it as the fully
        qualified domain name, and QATrack+ has FORCE_SCRIPT_NAME for a path
        prefix - but nothing validates the field, so it happens. This asserts
        only that such a value is given exactly one scheme and is not otherwise
        rewritten: the same output as before this change, so an installation
        configured that way sees no difference.

        Fixing the deployment is the deployment's business. Silently reshaping
        the value here would be worse than leaving it alone, because the result
        would be a working URL pointing somewhere nobody chose.
        """
        set_domain("HOST/appname")
        assert site_base_url() == "http://HOST/appname"

    def test_no_double_scheme_ever(self):
        for domain in [
            "example.com",
            "https://example.com",
            "http://example.com/",
            "HOST/appname",
            "https://example.com/appname",
        ]:
            set_domain(domain)
            url = site_base_url()
            assert url.count("://") == 1, "%r produced %r" % (domain, url)


@override_settings(HTTP_OR_HTTPS="http")
class TestReportLinks(SiteCacheCleanup, TestCase):
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
