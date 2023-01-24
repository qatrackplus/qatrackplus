from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django_q.models import Schedule

from qatrack.accounts.tests.utils import create_group, create_user
from qatrack.faults import models
from qatrack.faults.tests import utils as utils
from qatrack.notifications.faults import admin
from qatrack.notifications.models import FaultNotice, RecipientGroup, UnitGroup
from qatrack.qa.tests import utils as qa_utils


class TestFaultNoticeAdmin(TestCase):

    def setUp(self):

        self.user = create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')

        self.url_add = reverse(
            'admin:%s_%s_add' % (models.Fault._meta.app_label, models.Fault._meta.model_name)
        )
        self.url_list = reverse(
            'admin:%s_%s_changelist' % (
                FaultNotice._meta.app_label,
                FaultNotice._meta.model_name,
            )
        )

        self.admin = admin.FaultNoticeAdmin(model=FaultNotice, admin_site=AdminSite())

    def test_get_notification_type(self):
        """Ensure admin notifcation_type works as expected"""
        n = FaultNotice(pk=1, notification_type=FaultNotice.LOGGED)
        assert "Notify when fault logged" in self.admin.get_notification_type(n)

    def test_get_units(self):
        """Ensure admin notification units display works as expected"""
        u = qa_utils.create_unit(name="Test Unit")
        ug = UnitGroup.objects.create(name="UG")
        ug.units.add(u)
        rg = RecipientGroup.objects.create(name="RG")
        n = FaultNotice.objects.create(
            notification_type=FaultNotice.LOGGED,
            units=ug,
            recipients=rg,
        )
        assert ug.name in self.admin.get_units(n)

    def test_get_recipients(self):
        """Ensure admin notification recipients display works as expected"""
        rg = RecipientGroup.objects.create(name="RG")
        n = FaultNotice.objects.create(
            notification_type=FaultNotice.LOGGED,
            recipients=rg,
        )
        assert rg.name in self.admin.get_recipients(n)


class TestFaultNoticeEmails(TestCase):

    def setUp(self):

        self.tests = []

        self.unit = qa_utils.create_unit()

        self.unit_group = UnitGroup.objects.create(name="test group")
        self.unit_group.units.add(self.unit)

        self.group = create_group()
        user = create_user()
        user.groups.add(self.group)
        user.email = "example@example.com"
        user.save()
        self.utc = qa_utils.create_unit_test_collection(unit=self.unit)

        self.recipients = RecipientGroup.objects.create(name="test group")
        self.recipients.groups.add(self.group)

        self.inactive_user = models.User.objects.create_user('inactive', 'inactive@user.com', 'password')
        self.inactive_user.groups.add(self.group)
        self.inactive_user.is_active = False
        self.inactive_user.save()

        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

    def test_email_sent(self):
        """An email should be sent when a fault is created"""

        notification = FaultNotice.objects.create(
            notification_type=FaultNotice.LOGGED,
            recipients=self.recipients,
        )
        notification.save()
        utils.create_fault()
        self.assertEqual(len(mail.outbox), 1)

    def test_email_sent_after_create(self):
        notification = FaultNotice.objects.create(
            notification_type=FaultNotice.LOGGED,
            recipients=self.recipients,
        )
        notification.save()
        create_url = reverse("fault_create")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        user.groups.add(self.group)
        self.client.force_login(user)
        ft1 = models.FaultType.objects.create(code="fault type 1")
        ft2 = models.FaultType.objects.create(code="fault type 2")

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": [ft1.code, ft2.code],
            "fault-comment": "",
            "fault-related_service_events": [],
        }

        resp = self.client.post(create_url, data)
        assert resp.status_code == 302
        assert len(mail.outbox) == 1

    def test_email_not_sent_on_edit(self):
        """An email should not be sent when a fault is edited"""

        fault = utils.create_fault()
        FaultNotice.objects.create(
            notification_type=FaultNotice.LOGGED,
            recipients=self.recipients,
        )
        fault.save()
        self.assertEqual(len(mail.outbox), 0)

    def test_email_sent_to_group_for_unit(self):
        """An email should not be sent when when a fault is created for a unit belonging to a unit group"""

        FaultNotice.objects.create(
            notification_type=FaultNotice.LOGGED,
            recipients=self.recipients,
            units=self.unit_group,
        )
        utils.create_fault(unit=self.unit)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_not_sent_to_group_for_excluded_unit(self):
        """Fault is created on 2nd unit so no one should get an email"""

        FaultNotice.objects.create(
            notification_type=FaultNotice.LOGGED,
            recipients=self.recipients,
            units=self.unit_group,
        )

        utils.create_fault(unit=None)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_not_sent_to_group_for_unit(self):
        """Main group is not included in notification, only the new group, so only one email
        should be sent to the new user"""

        group2 = qa_utils.create_group(name="group2")
        rg = RecipientGroup.objects.create(name='group2')
        rg.groups.add(group2)
        FaultNotice.objects.create(
            notification_type=FaultNotice.LOGGED,
            recipients=rg,
            units=self.unit_group,
        )
        user2 = create_user(uname="user2")
        user2.email = "user2@example.com"
        user2.save()
        user2.groups.add(group2)
        utils.create_fault(unit=self.unit)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].recipients() == ['user2@example.com']

    def test_email_sent_to_group_and_single_user(self):
        """Main group is not included in notification, only new user, so only one email
        should be sent to the new user"""

        FaultNotice.objects.create(
            notification_type=FaultNotice.LOGGED,
            recipients=self.recipients,
        )
        user2 = create_user(uname="user2")
        user2.email = "user2@example.com"
        user2.save()
        self.recipients.users.add(user2)
        utils.create_fault(unit=self.unit)
        assert len(mail.outbox) == 1
        assert list(sorted(mail.outbox[0].recipients())) == ['example@example.com', 'user2@example.com']


class TestFaultNoticeModel:

    def test_str(self):
        n = FaultNotice(pk=1, notification_type=FaultNotice.LOGGED)
        assert str(n) == "<FaultNotice(1, Notify when fault logged)>"
