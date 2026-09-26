from django.test import Client, TestCase
from django.urls import reverse


class TestJavaScriptCatalogIsAnonymous(TestCase):
    """site_base.html loads the JS translation catalogue on every page.

    It does so with a plain <script src=...> tag, so if the URL is not
    exempt from LoginRequiredMiddleware the tag receives the login page's
    HTML instead of JavaScript. The browser reports that as
    "Uncaught SyntaxError: Unexpected token '<'" and the client-side
    catalogue silently never loads - `django.gettext` then returns its
    argument unchanged for the rest of the page.

    The exemption is easy to get wrong because the obvious pattern,
    "^i18n/", does not match "/jsi18n/".
    """

    def test_catalogue_is_served_to_anonymous_users(self):
        response = Client().get(reverse('javascript-catalog'))
        assert response.status_code == 200, (
            "the JS catalogue redirected (%s) instead of being served; check "
            "that LOGIN_EXEMPT_URLS covers jsi18n" % response.status_code
        )
        assert 'javascript' in response.headers['Content-Type']

    def test_response_is_javascript_not_html(self):
        """The failure mode is a 200-looking HTML page reaching a <script>
        tag, so assert on the body rather than only the status code."""
        body = Client().get(reverse('javascript-catalog')).content.decode('utf8')
        assert not body.lstrip().startswith('<'), "catalogue returned markup, not JavaScript"
        assert 'django' in body


class TestLoginExemptUrlsAreRegexesNotGlobs(TestCase):
    """LOGIN_EXEMPT_URLS entries are regexes, matched with re.match().

    Written as globs they quietly exempt more than intended: "api/*" reads as
    "api" followed by zero or more slashes, so it matched apifoo and
    api_secret as well as api/. Nothing exploitable followed from it - no
    route outside the DRF API starts with those letters, and the API answers
    anonymous requests with 401 on its own - but the next route added with an
    "api"-ish name would have become login-exempt silently.
    """

    def _exempt(self, path):
        from re import compile as re_compile

        from django.conf import settings

        patterns = [re_compile(e) for e in settings.LOGIN_EXEMPT_URLS]
        return any(p.match(path.lstrip("/")) for p in patterns)

    def test_intended_prefixes_are_still_exempt(self):
        for path in ["api", "api/", "api/qa/testlistinstances/", "oauth2/callback",
                     "i18n/setlang/", "jsi18n/", "accounts/login/", "favicon.ico"]:
            assert self._exempt(path), "%s should be exempt" % path

    def test_lookalike_prefixes_are_not_exempt(self):
        for path in ["apifoo", "api_secret", "apiary", "oauth2xyz", "faviconXico"]:
            assert not self._exempt(path), "%s should NOT be exempt" % path

    def test_application_paths_are_not_exempt(self):
        for path in ["qa/", "servicelog/", "admin/", "units/", "reports/"]:
            assert not self._exempt(path), "%s should NOT be exempt" % path

    def test_every_entry_is_anchored(self):
        """re.match anchors anyway; saying so keeps the intent readable."""
        from django.conf import settings

        unanchored = [e for e in settings.LOGIN_EXEMPT_URLS if not e.startswith("^")]
        assert not unanchored, "unanchored entries read as if they could match mid-path: %s" % unanchored
