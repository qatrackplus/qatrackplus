from django.contrib.auth.models import User
from django.test import TestCase
from django.test.utils import override_settings

from qatrack.accounts.admin import AdminFilter
from qatrack.accounts.backends import QATrackAccountBackend
from qatrack.accounts.backends import \
    ActiveDirectoryGroupMembershipSSLBackend as ADBack
from qatrack.qa.tests import utils


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

    @override_settings(ACCOUNTS_CLEAN_USERNAME=lambda u: u.lower())
    def test_accounts_clean(self):
        backend = QATrackAccountBackend()
        assert backend.clean_username("UserName") == "username"


class TestAdminFilter(TestCase):

    def test_lookups(self):
        assert AdminFilter.lookups(None, None, None) == (('yes', 'Yes'), ('no', 'No'))

    def test_queryset_yes(self):
        utils.create_user(uname="admin", is_staff=True, is_superuser=True)
        utils.create_user(uname="reg", is_staff=False, is_superuser=False)
        af = AdminFilter(None, [], None, None)
        af.value = lambda: 'yes'
        assert af.queryset(None, User.objects.all()).count() == 1

    def test_queryset_no(self):
        utils.create_user(uname="admin", is_staff=True, is_superuser=True)
        utils.create_user(uname="reg", is_staff=False, is_superuser=False)
        af = AdminFilter(None, [], None, None)
        af.value = lambda: 'no'
        assert af.queryset(None, User.objects.all()).count() == 1 + 1  # count Internal User
