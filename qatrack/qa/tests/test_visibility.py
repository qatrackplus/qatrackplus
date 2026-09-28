"""visible_to narrowing must not hide collections from users entitled to see all.

`visible_to` is a convenience for group members, not an authorisation boundary.
Filtering on user.groups alone hid every collection from a user in no groups -
including a superuser.  `qa.can_review_non_visible_tli` is the exemption.
"""

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from qatrack.qa import models
from qatrack.qa.tests import utils


class TestSeesAllCollections(TestCase):

    def setUp(self):
        self.group = Group.objects.create(name="Physics")
        self.other_group = Group.objects.create(name="Therapy")
        self.utc = utils.create_unit_test_collection()
        self.utc.visible_to.set([self.group])

        self.perm = Permission.objects.get(codename="can_review_non_visible_tli")

    def test_superuser_in_no_groups_sees_all(self):
        su = User.objects.create_superuser("su", "su@e.com", "pw")
        assert su.groups.count() == 0
        assert models.sees_all_collections(su) is True
        assert models.visible_groups_for(su) is None
        assert models.UnitTestCollection.objects.by_visibility(
            models.visible_groups_for(su)).filter(pk=self.utc.pk).exists()

    def test_plain_user_with_the_permission_sees_all(self):
        u = User.objects.create_user("holder", "h@e.com", "pw")
        u.user_permissions.add(self.perm)
        u = User.objects.get(pk=u.pk)          # clear the permission cache
        assert u.is_superuser is False
        assert models.sees_all_collections(u) is True
        assert models.UnitTestCollection.objects.by_visibility(
            models.visible_groups_for(u)).filter(pk=self.utc.pk).exists()

    def test_user_in_the_wrong_group_still_sees_nothing(self):
        """The narrowing must still narrow - this guards against over-widening."""
        u = User.objects.create_user("outsider", "o@e.com", "pw")
        u.groups.add(self.other_group)
        u = User.objects.get(pk=u.pk)
        assert models.sees_all_collections(u) is False
        groups = models.visible_groups_for(u)
        assert groups is not None
        assert not models.UnitTestCollection.objects.by_visibility(
            groups).filter(pk=self.utc.pk).exists()

    def test_user_in_the_right_group_sees_it(self):
        u = User.objects.create_user("insider", "i@e.com", "pw")
        u.groups.add(self.group)
        u = User.objects.get(pk=u.pk)
        assert models.UnitTestCollection.objects.by_visibility(
            models.visible_groups_for(u)).filter(pk=self.utc.pk).exists()

    def test_by_visibility_none_does_not_narrow(self):
        assert models.UnitTestCollection.objects.by_visibility(None).count() == \
            models.UnitTestCollection.objects.count()


class TestPerformQARespectsVisibility(TestCase):
    """The narrowing must survive at the view, not only in the manager.

    The first version of this change dropped `PerformQA`'s `visible_to` filter
    outright instead of making it conditional, so any user who could perform QC
    could open any collection's Perform page by typing its URL.  The listings
    stayed narrowed, so nothing above caught it; crane found it in a browser on
    Windows.  These tests pin the view itself.
    """

    def setUp(self):
        self.group = Group.objects.create(name="Physics")
        self.other_group = Group.objects.create(name="Therapy")

        self.mine = utils.create_unit_test_collection()
        self.mine.visible_to.set([self.group])
        self.theirs = utils.create_unit_test_collection(unit=self.mine.unit)
        self.theirs.visible_to.set([self.other_group])
        self.nobodys = utils.create_unit_test_collection(unit=self.mine.unit)
        self.nobodys.visible_to.set([])

        self.perform = Permission.objects.get(codename="add_testlistinstance")

    def url_for(self, utc):
        return reverse("perform_qa", kwargs={"pk": utc.pk})

    def make_user(self, username, groups=(), permissions=()):
        u = User.objects.create_user(username, "%s@e.com" % username, "pw")
        u.user_permissions.add(self.perform, *permissions)
        for g in groups:
            u.groups.add(g)
        return User.objects.get(pk=u.pk)      # clear the permission cache

    def test_plain_user_cannot_perform_another_groups_collection(self):
        self.make_user("physicist", groups=[self.group])
        self.client.login(username="physicist", password="pw")

        assert self.client.get(self.url_for(self.mine)).status_code == 200
        assert self.client.get(self.url_for(self.theirs)).status_code == 404
        assert self.client.get(self.url_for(self.nobodys)).status_code == 404

    def test_user_with_the_permission_can_perform_any_collection(self):
        self.make_user("holder", permissions=[
            Permission.objects.get(codename="can_review_non_visible_tli")])
        self.client.login(username="holder", password="pw")

        for utc in (self.mine, self.theirs, self.nobodys):
            assert self.client.get(self.url_for(utc)).status_code == 200

    def test_superuser_in_no_groups_can_perform_any_collection(self):
        User.objects.create_superuser("su", "su@e.com", "pw")
        self.client.login(username="su", password="pw")

        for utc in (self.mine, self.theirs, self.nobodys):
            assert self.client.get(self.url_for(utc)).status_code == 200
