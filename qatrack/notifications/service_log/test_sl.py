from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from django_q.models import Schedule

from qatrack.notifications.models import (
    RecipientGroup,
    ServiceEventNotice,
    UnitGroup,
)
from qatrack.notifications.service_log import admin
from qatrack.qa.tests import utils
from qatrack.service_log import models
from qatrack.service_log.tests import utils as sl_utils


class TestServiceLogEmails(TestCase):

    def setUp(self):
        self.unit1 = utils.create_unit(name="unit1", number=1)
        self.unit2 = utils.create_unit(name="unit2", number=2)
        self.utc1 = utils.create_unit_test_collection(unit=self.unit1)
        self.utc2 = utils.create_unit_test_collection(unit=self.unit2)

        self.unit_group = UnitGroup.objects.create(name="test group")
        self.unit_group.units.add(self.utc1.unit)

        self.group = Group.objects.latest('pk')
        self.user = User.objects.latest('pk')
        self.user.groups.add(self.group)
        self.user.email = "example@example.com"
        self.user.save()

        self.recipients = RecipientGroup.objects.create(name="test group")
        self.recipients.groups.add(self.group)

        self.inactive_user = User.objects.create_user('inactive', 'inactive@user.com', 'password')
        self.inactive_user.groups.add(self.group)
        self.inactive_user.is_active = False
        self.inactive_user.save()

        self.notice = ServiceEventNotice.objects.create(
            recipients=self.recipients,
            notification_type=ServiceEventNotice.UPDATED,
        )
        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

        self.sa = sl_utils.create_service_area()

    def test_created(self):
        se = sl_utils.create_service_event()
        models.ServiceLog.objects.create(
            user=self.user,
            log_type=models.NEW_SERVICE_EVENT,
            service_event=se,
        )
        assert len(mail.outbox) == 1
        assert "Service Event %s" % se in mail.outbox[0].subject

    def test_created_no_recipients(self):
        self.recipients.groups.clear()

        se = sl_utils.create_service_event()
        models.ServiceLog.objects.create(
            user=self.user,
            log_type=models.NEW_SERVICE_EVENT,
            service_event=se,
        )
        assert len(mail.outbox) == 0


class TestServiceLogAdmin(TestCase):

    def setUp(self):
        self.admin = admin.ServiceEventNoticeAdmin(model=ServiceEventNotice, admin_site=AdminSite())

    def test_get_notification_type_updated(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = ServiceEventNotice.objects.create(
            notification_type=ServiceEventNotice.UPDATED,
            recipients=rg,
        )
        assert "Notify when a Service Event is created or modified" in self.admin.get_notification_type(n)

    def test_get_units(self):
        u = utils.create_unit(name="Test Unit")
        ug = UnitGroup.objects.create(name="UG")
        ug.units.add(u)
        rg = RecipientGroup.objects.create(name="RG")
        n = ServiceEventNotice.objects.create(
            notification_type=ServiceEventNotice.UPDATED,
            units=ug,
            recipients=rg,
        )
        assert ug.name in self.admin.get_units(n)

    def test_get_recipients(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = ServiceEventNotice.objects.create(
            notification_type=ServiceEventNotice.UPDATED,
            recipients=rg,
        )
        assert rg.name in self.admin.get_recipients(n)
