from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_q.models import Schedule

from qatrack.accounts.tests.utils import create_user
from qatrack.notifications.models import (
    COMPLETED,
    FOLLOW_UP,
    TOLERANCE,
    NotificationSubscription,
)
from qatrack.notifications.tasks import send_follow_up_email
from qatrack.qa import models, signals
import qatrack.qa.tests.utils as utils


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

        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

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

        notification = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        notification.groups.add(self.group)
        notification.save()
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertEqual(len(mail.outbox), 1)

    def test_inactive_not_included(self):

        notification = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        notification.groups.add(self.group)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertNotIn(self.inactive_user.email, mail.outbox[0].recipients())

    def test_email_not_sent(self):
        # no failing tests so

        notification = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        notification.groups.add(self.group)

        self.test_list_instance.testinstance_set.update(pass_fail=models.OK)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_sent_to_group_for_unit(self):

        notification = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        notification.groups.add(self.group)
        notification.units.add(self.unit_test_collection.unit)

        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_not_sent_to_group_for_excluded_unit(self):
        """TLI is created on 2nd unit so no one should get an email"""

        utc2 = utils.create_unit_test_collection(test_collection=self.test_list)
        notification = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        notification.groups.add(self.group)
        notification.units.add(self.unit_test_collection.unit)

        tli = self.create_test_list_instance(utc=utc2)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_not_sent_to_group_for_unit(self):
        """Main group is not included in notification, only the new group, so only one email
        should be sent to the new user"""

        notification = NotificationSubscription.objects.create(notification_type=TOLERANCE)
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

        notification = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        notification.groups.add(self.group)
        user2 = utils.create_user(uname="user2")
        user2.email = "user2@example.com"
        user2.save()
        notification.users.add(user2)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        assert len(mail.outbox) == 1
        assert list(sorted(mail.outbox[0].recipients())) == ['example@example.com', 'user2@example.com']

    def test_email_sent_for_completion(self):

        notification = NotificationSubscription.objects.create(notification_type=COMPLETED)
        notification.groups.add(self.group)
        tli = self.create_test_list_instance(all_passing=True)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        assert len(mail.outbox) == 1
        assert "list was just completed" in mail.outbox[0].alternatives[0][0]

    def test_email_not_sent_for_completion_with_notification_type_tol(self):

        notification = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        notification.groups.add(self.group)
        tli = self.create_test_list_instance(all_passing=True)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        assert len(mail.outbox) == 0

    def test_email_not_sent_for_diff_testlist(self):

        new_test_list = utils.create_test_list()
        test = utils.create_test(name="new tl name")
        utils.create_test_list_membership(new_test_list, test)
        utc = utils.create_unit_test_collection(unit=self.unit_test_collection.unit, test_collection=new_test_list)

        notification = NotificationSubscription.objects.create(notification_type=COMPLETED)
        notification.test_lists.add(self.test_list)
        tli = self.create_test_list_instance(utc=utc)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        assert len(mail.outbox) == 0

    def test_email_sent_for_specific_testlist(self):

        notification = NotificationSubscription.objects.create(notification_type=COMPLETED)
        notification.test_lists.add(self.test_list)
        notification.groups.add(self.group)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        assert len(mail.outbox) == 1

    def test_email_not_sent_for_same_testlist_different_unit(self):

        unit = utils.create_unit()
        utc = utils.create_unit_test_collection(unit=unit, test_collection=self.test_list)

        notification = NotificationSubscription.objects.create(notification_type=COMPLETED)
        notification.test_lists.add(self.test_list)
        notification.units.add(self.unit_test_collection.unit)

        tli = self.create_test_list_instance(utc=utc)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        assert len(mail.outbox) == 0

    def test_follow_up_email_scheduled(self):

        notification = NotificationSubscription.objects.create(notification_type=FOLLOW_UP, follow_up_days=1)
        notification.test_lists.add(self.test_list)
        notification.groups.add(self.group)
        assert Schedule.objects.count() == 0
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        assert Schedule.objects.count() == 1

    def test_follow_up_email_tli_deleted(self):
        """Confirm deleting a test list instance removes scheduled follow ups"""

        notification = NotificationSubscription.objects.create(notification_type=FOLLOW_UP, follow_up_days=1)
        notification.test_lists.add(self.test_list)
        notification.groups.add(self.group)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        assert Schedule.objects.count() == 1
        self.test_list_instance.delete()
        assert Schedule.objects.count() == 0

    def test_follow_up_email_tli_edited(self):
        """Confirm editing a test list instance doesn't duplicate scheduled follow ups"""

        notification = NotificationSubscription.objects.create(notification_type=FOLLOW_UP, follow_up_days=1)
        notification.test_lists.add(self.test_list)
        notification.groups.add(self.group)
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=True)
        assert Schedule.objects.count() == 1
        scheduled = Schedule.objects.first().next_run
        self.test_list_instance.work_completed += timezone.timedelta(days=1)
        self.test_list_instance.save()
        signals.testlist_complete.send(sender=self, instance=self.test_list_instance, created=False)
        assert Schedule.objects.count() == 1
        assert Schedule.objects.first().next_run == scheduled + timezone.timedelta(days=1)

    def test_follow_up_not_sent_for_same_testlist_different_unit(self):

        unit = utils.create_unit()
        utc = utils.create_unit_test_collection(unit=unit, test_collection=self.test_list)

        notification = NotificationSubscription.objects.create(notification_type=FOLLOW_UP, follow_up_days=1)
        notification.test_lists.add(self.test_list)
        notification.units.add(self.unit_test_collection.unit)

        tli = self.create_test_list_instance(utc=utc)

        signals.testlist_complete.send(sender=self, instance=tli, created=True)
        assert Schedule.objects.count() == 0

    def test_send_follow_up_email(self):
        notification = NotificationSubscription.objects.create(notification_type=FOLLOW_UP, follow_up_days=1)
        notification.test_lists.add(self.test_list)
        notification.units.add(self.unit_test_collection.unit)
        notification.groups.add(self.group)
        send_follow_up_email(self.test_list_instance.id, notification.id)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_follow_up_email_no_notice(self):
        send_follow_up_email(self.test_list_instance.id)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_follow_up_email_no_tli(self):
        notification = NotificationSubscription.objects.create(notification_type=FOLLOW_UP, follow_up_days=1)
        send_follow_up_email(notification_id=notification.id)
        self.assertEqual(len(mail.outbox), 0)


class TestModels(TestCase):

    def test_str(self):
        n = NotificationSubscription(pk=1, notification_type=FOLLOW_UP)
        assert str(n) == "<NotificationSubscription(1, Follow up notification)>"


class TestNoticeAdmin(TestCase):

    def setUp(self):

        self.user = create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        self.url_add = reverse(
            'admin:%s_%s_add' % (NotificationSubscription._meta.app_label, NotificationSubscription._meta.model_name)
        )
        self.url_list = reverse(
            'admin:%s_%s_changelist' % (
                NotificationSubscription._meta.app_label,
                NotificationSubscription._meta.model_name,
            )
        )

        from qatrack.notifications import admin
        self.admin = admin.NotificationAdmin(model=NotificationSubscription, admin_site=AdminSite())

    def has_error(self, resp, err):
        return any(err in e for err_list in resp.context_data['errors'] for e in err_list)

    def test_add_completed_with_follow_up_days(self):
        """If the notification type is not follow up, then follow_up_days should not be set"""
        data = {
            'notification_type': TOLERANCE,
            'follow_up_days': 2,
        }

        resp = self.client.post(self.url_add, data=data)
        assert self.has_error(resp, "Leave 'Follow up days'")

    def test_add_follow_up_blank_days(self):
        data = {
            'notification_type': FOLLOW_UP,
            'follow_up_days': "",
        }
        resp = self.client.post(self.url_add, data=data)

        assert self.has_error(resp, "You must set the number of days")

    def test_add_follow_up_no_tl(self):
        data = {
            'notification_type': FOLLOW_UP,
            'follow_up_days': "2",
        }
        resp = self.client.post(self.url_add, data=data)

        assert self.has_error(resp, "You must select at least one Test List")

    def test_get_notification_type_follow_up(self):
        n = NotificationSubscription(pk=1, notification_type=FOLLOW_UP, follow_up_days=2)
        assert "Follow up notification (after 2 days)" in self.admin.get_notification_type(n)

    def test_get_notification_type_completed(self):
        n = NotificationSubscription(pk=1, notification_type=TOLERANCE, follow_up_days=2)
        assert "Tolerance" in self.admin.get_notification_type(n)

    def test_get_units(self):
        u = utils.create_unit(name="Test Unit")
        n = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        n.units.add(u)
        assert u.name in self.admin.get_units(n)

    def test_get_groups(self):
        g = utils.create_group(name="Group")
        n = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        n.groups.add(g)
        assert g.name in self.admin.get_groups(n)

    def test_get_users(self):
        u = utils.create_user()
        n = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        n.users.add(u)
        assert u.username in self.admin.get_users(n)

    def test_get_testlists(self):
        tl = utils.create_test_list(name="TL")
        n = NotificationSubscription.objects.create(notification_type=TOLERANCE)
        n.test_lists.add(tl)
        assert tl.name in self.admin.get_testlists(n)
