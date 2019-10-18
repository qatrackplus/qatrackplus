from django.test.utils import override_settings

from qatrack.accounts.backends import \
    ActiveDirectoryGroupMembershipSSLBackend as ADBack


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
