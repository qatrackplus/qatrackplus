from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.test.utils import override_settings

from qatrack.accounts import models
from qatrack.accounts.admin import AdminFilter
from qatrack.accounts.backends import (
    QATrackAccountBackend,
    QATrackAdfsAuthCodeBackend,
)
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


class TestADFSBackend(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("user")
        self.group1 = Group.objects.create(name="group1")
        self.group2 = Group.objects.create(name="group2")
        from django_auth_adfs.config import settings as adfs_settings
        adfs_settings.MIRROR_GROUPS = False

    def test_update_user_groups(self):

        be = QATrackAdfsAuthCodeBackend()
        claims = {'group': [self.group1.name, self.group2.name]}

        be.update_user_groups(self.user, claims)
        assert list(sorted(self.user.groups.values_list("pk", flat=True))) == list(
            sorted([self.group1.pk, self.group2.pk]),
        )

    def test_update_user_groups_with_mirror(self):

        claims = {'group': ['mirrored', self.group1.name, self.group2.name]}

        be = QATrackAdfsAuthCodeBackend()
        from django_auth_adfs.config import settings as adfs_settings
        adfs_settings.MIRROR_GROUPS = True
        be.update_user_groups(self.user, claims)
        g = Group.objects.get(name="mirrored")
        assert sorted(self.user.groups.values_list("pk", flat=True)) == sorted([self.group1.pk, self.group2.pk, g.pk])

    def test_update_user_groups_extra_no_mirror(self):

        be = QATrackAdfsAuthCodeBackend()
        claims = {'group': [self.group1.name, self.group2.name, 'donotcreate']}
        be.update_user_groups(self.user, claims)
        assert sorted(self.user.groups.values_list("pk", flat=True)) == sorted([self.group1.pk, self.group2.pk])

    def test_update_user_groups_existing_group(self):

        self.user.groups.add(self.group1)
        be = QATrackAdfsAuthCodeBackend()
        claims = {'group': [self.group2.name]}
        be.update_user_groups(self.user, claims)
        assert list(self.user.groups.order_by("name")) == [self.group1, self.group2]

    def test_update_with_map(self):

        claims = {'group': ['ad group 1']}
        m1 = models.ActiveDirectoryGroupMap.objects.create(ad_group='ad group 1')
        m1.groups.add(self.group1)
        m1.groups.add(self.group2)
        be = QATrackAdfsAuthCodeBackend()
        be.update_user_groups(self.user, claims)
        expected = list(sorted([self.group1.pk, self.group2.pk]))
        assert list(sorted(self.user.groups.values_list("pk", flat=True))) == expected

    def test_update_with_default_map(self):

        claims = {'group': ['ad group 1']}
        m1 = models.ActiveDirectoryGroupMap.objects.create(ad_group='ad group 1')
        m1.groups.add(self.group1)

        m2 = models.ActiveDirectoryGroupMap.objects.create(ad_group='')
        m2.groups.add(self.group2)

        be = QATrackAdfsAuthCodeBackend()
        be.update_user_groups(self.user, claims)
        expected = list(sorted([self.group1.pk, self.group2.pk]))
        assert list(sorted(self.user.groups.values_list("pk", flat=True))) == expected
