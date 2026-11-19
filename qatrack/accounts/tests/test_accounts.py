from unittest import mock

import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.test.utils import override_settings
from django_auth_adfs.backend import AdfsAuthCodeBackend

from qatrack.accounts import models
from qatrack.accounts.admin import AdminFilter
from qatrack.accounts.backends import ActiveDirectoryGroupMembershipSSLBackend as ADBack
from qatrack.accounts.backends import (
    QATrackAccountBackend,
    QATrackAdfsAuthCodeBackend,
)
from qatrack.qa.tests import utils


class TestCleanUsername:

    def test_no_clean(self):
        ldap = pytest.importorskip("ldap")  # noqa:F841,F811
        backend = ADBack()
        assert backend.clean_username("foo") == "foo"

    @override_settings(AD_CLEAN_USERNAME=lambda x: x.lower())
    def test_clean(self):
        ldap = pytest.importorskip("ldap")  # noqa:F841,F811
        backend = ADBack()
        assert backend.clean_username("Foo") == "foo"

    @override_settings(AD_CLEAN_USERNAME=None, AD_CLEAN_USERNAME_STRING="Foo/")
    def test_replace(self):
        ldap = pytest.importorskip("ldap")  # noqa:F841,F811
        backend = ADBack()
        assert backend.clean_username("Foo/bar") == "bar"

    @override_settings(ACCOUNTS_CLEAN_USERNAME=lambda u: u.lower())
    def test_accounts_clean(self):
        backend = QATrackAccountBackend()
        assert backend.clean_username("UserName") == "username"


class TestAdminFilter(TestCase):

    def test_lookups(self):
        assert AdminFilter.lookups(None, None, None) == (('yes', 'Yes'), ('no', 'No'))

    # These two filter `User.objects` down to the pair they create rather than
    # counting the whole table. Counting everything made them depend on which
    # accounts the database already held, which is not a property of the filter:
    # `test_queryset_no` already carried a `1 + 1  # count Internal User` to
    # absorb the account a migration creates, and `test_queryset_yes` failed
    # outright under `poe test-integration` / `make test-integration`, which
    # provisions the database the way a deployment does and so leaves the
    # `superuser` account `createsuperuser` makes in it. @nsmela reported that
    # on #868: a correct tree gave 1 failed, 1742 passed, with
    # `assert 2 == 1` here.
    #
    # Scoping the queryset is the fix rather than dropping `createsuperuser`
    # from that task, which exists precisely to exercise the real provisioning
    # sequence.
    OWN_USERS = ["admin-filter-admin", "admin-filter-regular"]

    def create_the_pair(self):
        utils.create_user(uname=self.OWN_USERS[0], is_staff=True, is_superuser=True)
        utils.create_user(uname=self.OWN_USERS[1], is_staff=False, is_superuser=False)
        return User.objects.filter(username__in=self.OWN_USERS)

    def test_queryset_yes(self):
        own = self.create_the_pair()
        af = AdminFilter(None, [], None, None)
        af.value = lambda: 'yes'

        assert list(af.queryset(None, own).values_list('username', flat=True)) == [self.OWN_USERS[0]]

    def test_queryset_no(self):
        own = self.create_the_pair()
        af = AdminFilter(None, [], None, None)
        af.value = lambda: 'no'

        assert list(af.queryset(None, own).values_list('username', flat=True)) == [self.OWN_USERS[1]]

    def test_the_answer_does_not_depend_on_other_accounts_in_the_table(self):
        """The regression, stated as a property rather than left to the count.

        An account this test did not create must not change what the filter
        returns. `poe test-integration` provisions the database the way a
        deployment does, so a `superuser` account is sitting in the
        `--reuse-db` database before the suite starts - and that is exactly
        what the old whole-table count could not survive.
        """
        utils.create_user(uname="provisioned-superuser", is_staff=True, is_superuser=True)
        own = self.create_the_pair()
        af = AdminFilter(None, [], None, None)

        af.value = lambda: 'yes'
        assert list(af.queryset(None, own).values_list('username', flat=True)) == [self.OWN_USERS[0]]
        af.value = lambda: 'no'
        assert list(af.queryset(None, own).values_list('username', flat=True)) == [self.OWN_USERS[1]]


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

        models.DefaultGroup.objects.create(group=self.group2)

        be = QATrackAdfsAuthCodeBackend()
        be.update_user_groups(self.user, claims)
        expected = list(sorted([self.group1.pk, self.group2.pk]))
        assert list(sorted(self.user.groups.values_list("pk", flat=True))) == expected


class TestADFSCreateUser(TestCase):

    def setUp(self):
        from django_auth_adfs.config import settings as adfs_settings
        adfs_settings.MIRROR_GROUPS = False
        self.backend = QATrackAdfsAuthCodeBackend()

    def claims(self, **over):
        c = {
            "winaccountname": "jdoe",
            "given_name": "Jane", "family_name": "Doe",
            "email": "jdoe@example.com",
            "group": ["Physicists"],
        }
        c.update(over)
        return c

    def test_no_qualifying_groups_lets_anyone_in(self):
        # No account_qualifier groups defined -> gate is skipped
        user = self.backend.create_user(self.claims())
        assert user.username == "jdoe"

    def test_qualifying_group_match_allowed(self):
        models.ActiveDirectoryGroupMap.objects.create(
            ad_group="Physicists", account_qualifier=True,
        )
        user = self.backend.create_user(self.claims(group=["Physicists"]))
        assert user.username == "jdoe"

    def test_qualifying_group_mismatch_denied(self):
        models.ActiveDirectoryGroupMap.objects.create(
            ad_group="Admins", account_qualifier=True,
        )
        with self.assertRaises(PermissionDenied):
            self.backend.create_user(self.claims(group=["Physicists"]))

    @override_settings(ACCOUNTS_CLEAN_USERNAME=lambda u: u.lower())
    def test_username_cleaned_on_create(self):
        user = self.backend.create_user(self.claims(winaccountname="JDoe"))
        assert user.username == "jdoe"

    def test_claim_mapping_populates_user_attributes(self):
        # CLAIM_MAPPING (first_name/last_name/email) is applied by the parent
        user = self.backend.create_user(self.claims())
        self.backend.update_user_attributes(user, self.claims())
        assert user.first_name == "Jane"
        assert user.last_name == "Doe"
        assert user.email == "jdoe@example.com"

    def test_authenticate_returns_none_on_permission_denied(self):
        # QATrack+ overrides authenticate to swallow PermissionDenied -> None
        with mock.patch.object(AdfsAuthCodeBackend, "authenticate", side_effect=PermissionDenied):
            assert self.backend.authenticate(authorization_code="x") is None
