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
