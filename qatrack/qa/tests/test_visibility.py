"""visible_to narrowing must not hide collections from users entitled to see all.

`visible_to` is a convenience for group members, not an authorisation boundary.
Filtering on user.groups alone hid every collection from a user in no groups -
including a superuser.  `qa.can_review_non_visible_tli` is the exemption.
"""

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from qatrack.qa import models, trees
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


class TestTreesDoNotCollapseCollectionsSharingAName(TestCase):
    """Two collections with the same name must both appear in the trees.

    The tree queries join through test membership, so a collection appears once
    per test and the duplicates have to be collapsed. That was done by name -
    which also collapses two *different* collections that happen to share one,
    dropping one of them from the tree entirely, with no way to reach its Perform
    page from there.

    `UnitTestCollection.name` is derived and not unique, so this is ordinary
    rather than contrived. It became reachable when this branch let a holder of
    `qa.can_review_non_visible_tli` see every group's collections at once:
    narrowed to one group, two same-named collections rarely met.
    """

    def setUp(self):
        self.unit = utils.create_unit()
        self.frequency = utils.create_frequency(name="daily-collapse", slug="daily-collapse")

        # each collection needs a test in a category, or the category tree's
        # query - which joins through test membership - excludes it entirely
        category = utils.create_category(name="collapse-cat", slug="collapse-cat")

        first_list = utils.create_test_list("collapse list one")
        utils.create_test_list_membership(
            test_list=first_list,
            test=utils.create_test(name="collapse-t1", category=category),
        )
        second_list = utils.create_test_list("collapse list two")
        utils.create_test_list_membership(
            test_list=second_list,
            test=utils.create_test(name="collapse-t2", category=category),
        )

        self.first = utils.create_unit_test_collection(
            unit=self.unit, frequency=self.frequency, test_collection=first_list)
        self.second = utils.create_unit_test_collection(
            unit=self.unit, frequency=self.frequency, test_collection=second_list)

        # the collision: derived, not unique, so two can share one
        models.UnitTestCollection.objects.filter(
            pk__in=[self.first.pk, self.second.pk]
        ).update(name="Daily QC")

    def ids_in(self, tree):
        """Every UnitTestCollection id the rendered tree links to."""
        import json
        import re
        return set(int(m) for m in re.findall(r'/qc/utc/perform/(\d+)/', json.dumps(tree)))

    def test_the_frequency_tree_shows_both(self):
        tree = trees.BootstrapFrequencyTree(None).generate()
        found = self.ids_in(tree)
        assert {self.first.pk, self.second.pk} <= found, (
            "only %s reached the frequency tree; a collection sharing a name was "
            "dropped" % sorted(found)
        )

    def test_the_category_tree_shows_both(self):
        tree = trees.BootstrapCategoryTree(None).generate()
        found = self.ids_in(tree)
        assert {self.first.pk, self.second.pk} <= found, (
            "only %s reached the category tree; a collection sharing a name was "
            "dropped" % sorted(found)
        )

    def test_a_collection_with_several_tests_still_appears_once(self):
        """The collapsing itself still has to happen.

        The tree queries join through test membership, so a collection comes back
        once per test it contains. Without this test, deleting the deduplication
        outright would satisfy both of the assertions above.
        """
        import json
        import re

        category = utils.create_category(name="collapse-cat-two", slug="collapse-cat-two")
        test_list = utils.create_test_list("collapse list three")
        for name in ("collapse-t3", "collapse-t4"):
            utils.create_test_list_membership(
                test_list=test_list,
                test=utils.create_test(name=name, category=category),
            )
        utc = utils.create_unit_test_collection(
            unit=self.unit, frequency=self.frequency, test_collection=test_list)

        for which, tree in (
            ("frequency", trees.BootstrapFrequencyTree(None).generate()),
            ("category", trees.BootstrapCategoryTree(None).generate()),
        ):
            hits = re.findall(r'/qc/utc/perform/%d/' % utc.pk, json.dumps(tree))
            assert len(hits) == 1, (
                "a collection with two tests in one category appeared %d times in the "
                "%s tree" % (len(hits), which)
            )
