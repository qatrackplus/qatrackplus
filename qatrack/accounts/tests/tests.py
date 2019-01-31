from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse

from qatrack.accounts import views
from qatrack.accounts.backends import \
    ActiveDirectoryGroupMembershipSSLBackend as ADBack
from qatrack.qa.tests import utils
from qatrack.qatrack_core.tests.utils import setup_view


class TestCleanUsername:

    def test_no_clean(self):
        backend = ADBack()
        assert backend.clean_username("foo") == "foo"

    @override_settings(AD_CLEAN_USERNAME=lambda x: x.lower())
    def test_clean(self):
        backend = ADBack()
        assert backend.clean_username("Foo") == "foo"

    @override_settings(AD_CLEAN_USERNAME=None, AD_CLEAN_USERNAME_STRING="Foo/")
    def test_replace(self):
        backend = ADBack()
        assert backend.clean_username("Foo/bar") == "bar"


#class TestAccountViews:
#
#    def setUp(self):
#        self.group =
#
#
#    def test_account_details(self):
#        request = RequestFactory().get(reverse("account-details"))
#        request.user = self.user
#        v = setup_view(views.AccountDetails(), request)
#        context = v.get_context_data()
#        import ipdb; ipdb.set_trace()  # yapf: disable  # noqa
#        assert False
