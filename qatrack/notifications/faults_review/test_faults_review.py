from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule
import recurrence

from qatrack.faults.models import Fault
import qatrack.faults.tests.utils as utils
from qatrack.notifications.faults_review import admin, tasks
from qatrack.notifications.models import (
    FaultsReviewNotice,
    RecipientGroup,
    UnitGroup,
)
from qatrack.qa import models
import qatrack.qa.tests.utils as qa_utils


class TestFaultsReviewAdmin(TestCase):

    def setUp(self):
        self.admin = admin.FaultsReviewAdmin(model=FaultsReviewNotice, admin_site=AdminSite())

    def test_get_notification_type_unreviewed(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = FaultsReviewNotice.objects.create(
            notification_type=FaultsReviewNotice.UNREVIEWED,
            time="0:00",
            recipients=rg,
        )
        assert "Notify about Faults awaiting review" in self.admin.get_notification_type(n)

    def test_get_units(self):
        u = qa_utils.create_unit(name="Test Unit")
        ug = UnitGroup.objects.create(name="UG")
        ug.units.add(u)
        rg = RecipientGroup.objects.create(name="RG")
        n = FaultsReviewNotice.objects.create(
            notification_type=FaultsReviewNotice.UNREVIEWED,
            units=ug,
            recipients=rg,
            time="0:00",
        )
        assert ug.name in self.admin.get_units(n)

    def test_get_recipients(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = FaultsReviewNotice.objects.create(
            notification_type=FaultsReviewNotice.UNREVIEWED,
            recipients=rg,
            time="0:00",
        )
        assert rg.name in self.admin.get_recipients(n)


class TestFaultsReviewModel(TestCase):

    def setUp(self):

        self.unit1 = qa_utils.create_unit(name="unit1", number=1)
        self.unit2 = qa_utils.create_unit(name="unit2", number=2)

        self.fault1 = utils.create_fault(unit=self.unit1)
        self.fault2 = utils.create_fault(unit=self.unit2)

        self.unit_group = UnitGroup.objects.create(name="test group")
        self.unit_group.units.add(self.unit1)

        self.group = qa_utils.create_group()
        self.user = models.User.objects.latest('pk')
        self.user.is_active = True
        self.user.groups.add(self.group)
        self.user.email = "example@example.com"
        self.user.save()

        self.recipients = RecipientGroup.objects.create(name="test group")
        self.recipients.groups.add(self.group)

        self.inactive_user = models.User.objects.create_user('inactive', 'inactive@user.com', 'password')
        self.inactive_user.groups.add(self.group)
        self.inactive_user.is_active = False
        self.inactive_user.save()

        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

    def test_unreviewed_both_unreviewed_no_groups(self):

        notice = FaultsReviewNotice.objects.create(
            recipients=self.recipients,
            notification_type=FaultsReviewNotice.UNREVIEWED,
            time="0:00",
        )
        expected = [
            {
                'unit__name': self.unit1.name,
                'fault_types__code': self.fault1.fault_types.first().code,
                'unit__name__count': 1,
                'fault_types__code__count': 1,
            },
            {
                'unit__name': self.unit2.name,
                'fault_types__code': self.fault2.fault_types.first().code,
                'unit__name__count': 1,
                'fault_types__code__count': 1,
            },
        ]
        assert list(notice.faults_by_unit_fault_type()) == expected

    def test_upcoming_both_unreviewed_unit_group(self):
        utils.create_fault_review(fault=self.fault2, reviewed_by=self.user)

        notice = FaultsReviewNotice.objects.create(
            recipients=self.recipients,
            units=self.unit_group,
            notification_type=FaultsReviewNotice.UNREVIEWED,
            time="0:00",
        )
        expected = [
            {
                'unit__name': self.unit1.name,
                'fault_types__code': self.fault1.fault_types.first().code,
                'unit__name__count': 1,
                'fault_types__code__count': 1,
            },
        ]
        assert list(notice.faults_by_unit_fault_type()) == expected

    def test_is_props(self):
        assert FaultsReviewNotice(notification_type=FaultsReviewNotice.UNREVIEWED).is_unreviewed


class TestFaultsReviewEmails(TestCase):

    def setUp(self):

        self.unit1 = qa_utils.create_unit(name="unit1", number=1)
        self.unit2 = qa_utils.create_unit(name="unit2", number=2)
        self.faults1 = utils.create_fault(unit=self.unit1)
        self.faults2 = utils.create_fault(unit=self.unit2)

        self.unit_group = UnitGroup.objects.create(name="test group")
        self.unit_group.units.add(self.unit1)

        self.group = qa_utils.create_group()
        self.user = models.User.objects.latest('pk')
        self.user.groups.add(self.group)
        self.user.is_active = True
        self.user.email = "example@example.com"
        self.user.save()

        self.recipients = RecipientGroup.objects.create(name="test group")
        self.recipients.groups.add(self.group)

        self.inactive_user = models.User.objects.create_user('inactive', 'inactive@user.com', 'password')
        self.inactive_user.groups.add(self.group)
        self.inactive_user.is_active = False
        self.inactive_user.save()

        self.notice = FaultsReviewNotice.objects.create(
            recipients=self.recipients,
            notification_type=FaultsReviewNotice.UNREVIEWED,
            time="0:00",
        )
        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

    def test_send_notice(self):
        self.faults1 = utils.create_fault()
        now = timezone.now()
        tasks.send_faultsreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent >= now
        assert "QATrack+ Unreviewed Faults Notice:" in mail.outbox[0].subject

    def test_send_notice_empty(self):
        self.notice.send_empty = True
        self.notice.save()
        now = timezone.now()
        tasks.send_faultsreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent >= now
        assert "QATrack+ Unreviewed Faults Notice:" in mail.outbox[0].subject

    def test_send_notice_not_empty(self):
        for fault in Fault.objects.all():
            utils.create_fault_review(fault=fault, reviewed_by=self.user)
        tasks.send_faultsreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert len(mail.outbox) == 0

    def test_send_notice_non_existent(self):
        tasks.send_faultsreview_notice(self.notice.pk + 1)
        self.notice.refresh_from_db()
        assert self.notice.last_sent is None
        assert len(mail.outbox) == 0

    def test_send_notice_no_recipients(self):
        utils.create_fault()
        self.recipients.groups.clear()
        tasks.send_faultsreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent is None
        assert len(mail.outbox) == 0

    def test_review_notice(self):
        next_run = timezone.now() + timezone.timedelta(hours=1)
        tasks.schedule_faultsreview_notice(self.notice, next_run)
        assert Schedule.objects.count() == 1

    def test_run_review_notices(self):
        self.notice.recurrences = recurrence.Recurrence(rrules=[recurrence.Rule(recurrence.DAILY)])
        self.notice.time = (timezone.localtime(timezone.now()) + timezone.timedelta(minutes=1)).time()
        self.notice.save()
        tasks.run_faults_review_notices()
        assert Schedule.objects.count() == 1
