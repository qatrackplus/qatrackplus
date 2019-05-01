from django.core import mail
from django.test import TestCase

from qatrack.qa import models, signals
import qatrack.qa.tests.utils as utils

from .models import COMPLETED, TOLERANCE, NotificationSubscription


class TestEmailSent(TestCase):

    def setUp(self):

        self.tests = []

        self.ref = models.Reference(type=models.NUMERICAL, value=100.)
        self.tol = models.Tolerance(type=models.PERCENT, act_low=-3, tol_low=-2, tol_high=2, act_high=3)
        self.ref.created_by = utils.create_user()
        self.tol.created_by = utils.create_user()
        self.ref.modified_by = utils.create_user()
        self.tol.modified_by = utils.create_user()
        self.values = [None, None, 96, 97, 100, 100]

        self.statuses = [utils.create_status(name="status%d" % x, slug="status%d" % x) for x in range(len(self.values))]

        self.test_list = utils.create_test_list()
        for i in range(6):
            test = utils.create_test(name="name%d" % i)
            self.tests.append(test)
            utils.create_test_list_membership(self.test_list, test)

        self.unit_test_collection = utils.create_unit_test_collection(test_collection=self.test_list)

        self.test_list_instance = self.create_test_list_instance()

        self.group = models.Group.objects.latest('pk')
        user = models.User.objects.latest('pk')
        user.groups.add(self.group)
        user.email = "example@example.com"
        user.save()

        self.inactive_user = models.User.objects.create_user('inactive', 'a@b.com', 'password')
        self.inactive_user.groups.add(self.group)
        self.inactive_user.is_active = False
        self.inactive_user.save()

    def create_test_list_instance(self, utc=None, all_passing=False):
        utc = utc or self.unit_test_collection

        tli = utils.create_test_list_instance(unit_test_collection=utc)

        for i, (v, test, status) in enumerate(zip(self.values, self.tests, self.statuses)):
            uti = models.UnitTestInfo.objects.get(test=test, unit=utc.unit)
            ti = utils.create_test_instance(tli, unit_test_info=uti, value=v, status=status)
            ti.reference = self.ref
            ti.tolerance = self.tol
            if i == 0:
                ti.skipped = True
            if i == 1 or all_passing:
                ti.tolerance = None
                ti.reference = None
            else:
                ti.reference.save()
                ti.tolerance.save()

            ti.save()
        tli.save()
        return tli

    def test_email_sent(self):

        notification = NotificationSubscription.objects.create(warning_level=TOLERANCE)
        notification.groups.add(self.group)
        notification.save()
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertEqual(len(mail.outbox), 1)

    def test_inactive_not_included(self):

        notification = NotificationSubscription.objects.create(warning_level=TOLERANCE)
        notification.groups.add(self.group)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertNotIn(self.inactive_user.email, mail.outbox[0].recipients())

    def test_email_not_sent(self):
        # no failing tests so

        notification = NotificationSubscription.objects.create(warning_level=TOLERANCE)
        notification.groups.add(self.group)

        self.test_list_instance.testinstance_set.update(pass_fail=models.OK)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_sent_to_group_for_unit(self):

        notification = NotificationSubscription.objects.create(warning_level=TOLERANCE)
        notification.groups.add(self.group)
        notification.units.add(self.unit_test_collection.unit)

        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_not_sent_to_group_for_excluded_unit(self):
        """TLI is created on 2nd unit so no one should get an email"""

        utc2 = utils.create_unit_test_collection(test_collection=self.test_list)
        notification = NotificationSubscription.objects.create(warning_level=TOLERANCE)
        notification.groups.add(self.group)
        notification.units.add(self.unit_test_collection.unit)

        tli = self.create_test_list_instance(utc=utc2)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_not_sent_to_group_for_unit(self):
        """Main group is not included in notification, only the new group, so only one email
        should be sent to the new user"""

        notification = NotificationSubscription.objects.create(warning_level=TOLERANCE)
        group2 = utils.create_group(name="group2")
        notification.groups.add(group2)
        user2 = utils.create_user(uname="user2")
        user2.email = "user2@example.com"
        user2.save()
        user2.groups.add(group2)
        notification.units.add(self.unit_test_collection.unit)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].recipients() == ['user2@example.com']

    def test_email_sent_to_group_and_single_user(self):
        """Main group is not included in notification, only new user, so only one email
        should be sent to the new user"""

        notification = NotificationSubscription.objects.create(warning_level=TOLERANCE)
        notification.groups.add(self.group)
        user2 = utils.create_user(uname="user2")
        user2.email = "user2@example.com"
        user2.save()
        notification.users.add(user2)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        assert len(mail.outbox) == 1
        assert list(sorted(mail.outbox[0].recipients())) == ['example@example.com', 'user2@example.com']

    def test_email_sent_for_completion(self):

        notification = NotificationSubscription.objects.create(warning_level=COMPLETED)
        notification.groups.add(self.group)
        tli = self.create_test_list_instance(all_passing=True)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        assert len(mail.outbox) == 1
        assert "list was just completed" in mail.outbox[0].alternatives[0][0]

    def test_email_not_sent_for_completion_with_warning_level_tol(self):

        notification = NotificationSubscription.objects.create(warning_level=TOLERANCE)
        notification.groups.add(self.group)
        tli = self.create_test_list_instance(all_passing=True)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        assert len(mail.outbox) == 0

    def test_email_not_sent_for_diff_testlist(self):

        new_test_list = utils.create_test_list()
        test = utils.create_test(name="new tl name")
        utils.create_test_list_membership(new_test_list, test)
        utc = utils.create_unit_test_collection(unit=self.unit_test_collection.unit, test_collection=new_test_list)

        notification = NotificationSubscription.objects.create(warning_level=COMPLETED)
        notification.test_lists.add(self.test_list)
        tli = self.create_test_list_instance(utc=utc)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        assert len(mail.outbox) == 0

    def test_email_sent_for_specific_testlist(self):

        notification = NotificationSubscription.objects.create(warning_level=COMPLETED)
        notification.test_lists.add(self.test_list)
        notification.groups.add(self.group)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        assert len(mail.outbox) == 1

    def test_email_not_sent_for_same_testlist_different_unit(self):

        unit = utils.create_unit()
        utc = utils.create_unit_test_collection(unit=unit, test_collection=self.test_list)

        notification = NotificationSubscription.objects.create(warning_level=COMPLETED)
        notification.test_lists.add(self.test_list)
        notification.units.add(self.unit_test_collection.unit)

        tli = self.create_test_list_instance(utc=utc)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        assert len(mail.outbox) == 0
