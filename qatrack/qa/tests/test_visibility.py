"""visible_to narrowing must not hide collections from users entitled to see all.

`visible_to` is a convenience for group members, not an authorisation boundary.
Filtering on user.groups alone hid every collection from a user in no groups -
including a superuser.  `qa.can_review_non_visible_tli` is the exemption.
"""

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase

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
