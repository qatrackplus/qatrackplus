from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule
import recurrence

from qatrack.notifications.models import (
    QCReviewNotice,
    RecipientGroup,
    TestListGroup,
    UnitGroup,
)
from qatrack.notifications.qcreview import admin, tasks
from qatrack.qa import models
import qatrack.qa.tests.utils as utils


class TestQCReviewAdmin(TestCase):

    def setUp(self):
        self.admin = admin.QCReviewAdmin(model=QCReviewNotice, admin_site=AdminSite())

    def test_get_notification_type_unreviewed(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = QCReviewNotice.objects.create(
            notification_type=QCReviewNotice.UNREVIEWED,
            time="0:00",
            recipients=rg,
        )
        assert "Notify about test list instances awaiting review" in self.admin.get_notification_type(n)

    def test_get_units(self):
        u = utils.create_unit(name="Test Unit")
        ug = UnitGroup.objects.create(name="UG")
        ug.units.add(u)
        rg = RecipientGroup.objects.create(name="RG")
        n = QCReviewNotice.objects.create(
            notification_type=QCReviewNotice.UNREVIEWED,
            units=ug,
            recipients=rg,
            time="0:00",
        )
        assert ug.name in self.admin.get_units(n)

    def test_get_recipients(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = QCReviewNotice.objects.create(
            notification_type=QCReviewNotice.UNREVIEWED,
            recipients=rg,
            time="0:00",
        )
        assert rg.name in self.admin.get_recipients(n)

    def test_get_testlists(self):
        tl = utils.create_test_list(name="TL")
        rg = RecipientGroup.objects.create(name="RG")
        tlg = TestListGroup.objects.create(name="TLG")
        tlg.test_lists.add(tl)
        n = QCReviewNotice.objects.create(
            notification_type=QCReviewNotice.UNREVIEWED,
            recipients=rg,
            test_lists=tlg,
            time="0:00",
        )
        assert tlg.name in self.admin.get_testlists(n)


class TestQCReviewModel(TestCase):

    def setUp(self):

        self.unit1 = utils.create_unit(name="unit1", number=1)
        self.unit2 = utils.create_unit(name="unit2", number=2)
        self.utc1 = utils.create_unit_test_collection(unit=self.unit1)
        self.utc2 = utils.create_unit_test_collection(unit=self.unit2)

        self.tli1 = utils.create_test_list_instance(unit_test_collection=self.utc1)
        self.tli1.all_reviewed = False
        self.tli1.save()
        self.tli2 = utils.create_test_list_instance(unit_test_collection=self.utc2)
        self.tli2.all_reviewed = True
        self.tli2.save()

        self.testlist_group = TestListGroup.objects.create(name="test group")
        self.testlist_group.test_lists.add(self.utc1.tests_object)

        self.unit_group = UnitGroup.objects.create(name="test group")
        self.unit_group.units.add(self.utc1.unit)

        self.group = models.Group.objects.latest('pk')
        user = models.User.objects.latest('pk')
        user.groups.add(self.group)
        user.email = "example@example.com"
        user.save()

        self.recipients = RecipientGroup.objects.create(name="test group")
        self.recipients.groups.add(self.group)

        self.inactive_user = models.User.objects.create_user('inactive', 'inactive@user.com', 'password')
        self.inactive_user.groups.add(self.group)
        self.inactive_user.is_active = False
        self.inactive_user.save()

        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

    def test_unreviewed_both_unreviewed_no_groups(self):
        self.tli1.all_reviewed = False
        self.tli1.save()
        self.tli2.all_reviewed = False
        self.tli2.save()

        notice = QCReviewNotice.objects.create(
            recipients=self.recipients,
            notification_type=QCReviewNotice.UNREVIEWED,
            time="0:00",
        )
        expected = [
            {
                'unit_test_collection__unit__name': self.utc1.unit.name,
                'unit_test_collection__name': self.utc1.name,
                'unit_test_collection__unit__name__count': 1,
                'unit_test_collection__name__count': 1,
            },
            {
                'unit_test_collection__unit__name': self.utc2.unit.name,
                'unit_test_collection__name': self.utc2.name,
                'unit_test_collection__unit__name__count': 1,
                'unit_test_collection__name__count': 1,
            },
        ]
        assert list(notice.tlis_by_unit_utc()) == expected

    def test_upcoming_both_unreviewed_unit_group(self):
        self.tli1.all_reviewed = False
        self.tli1.save()
        self.tli2.all_reviewed = False
        self.tli2.save()

        notice = QCReviewNotice.objects.create(
            recipients=self.recipients,
            units=self.unit_group,
            notification_type=QCReviewNotice.UNREVIEWED,
            time="0:00",
        )
        expected = [
            {
                'unit_test_collection__unit__name': self.utc1.unit.name,
                'unit_test_collection__name': self.utc1.name,
                'unit_test_collection__unit__name__count': 1,
                'unit_test_collection__name__count': 1,
            },
        ]
        assert list(notice.tlis_by_unit_utc()) == expected

    def test_upcoming_both_overdue_testlist_group(self):
        self.tli1.all_reviewed = False
        self.tli1.save()
        self.tli1.all_reviewed = False
        self.tli1.save()

        notice = QCReviewNotice.objects.create(
            recipients=self.recipients,
            test_lists=self.testlist_group,
            notification_type=QCReviewNotice.UNREVIEWED,
            time="0:00",
        )
        expected = [
            {
                'unit_test_collection__unit__name': self.utc1.unit.name,
                'unit_test_collection__name': self.utc1.name,
                'unit_test_collection__unit__name__count': 1,
                'unit_test_collection__name__count': 1,
            },
        ]
        assert list(notice.tlis_by_unit_utc()) == expected

    def test_is_props(self):
        assert QCReviewNotice(notification_type=QCReviewNotice.UNREVIEWED).is_unreviewed


class TestQCReviewEmails(TestCase):

    def setUp(self):

        self.unit1 = utils.create_unit(name="unit1", number=1)
        self.unit2 = utils.create_unit(name="unit2", number=2)
        self.utc1 = utils.create_unit_test_collection(unit=self.unit1)
        self.utc2 = utils.create_unit_test_collection(unit=self.unit2)

        self.testlist_group = TestListGroup.objects.create(name="test group")
        self.testlist_group.test_lists.add(self.utc1.tests_object)

        self.unit_group = UnitGroup.objects.create(name="test group")
        self.unit_group.units.add(self.utc1.unit)

        self.group = models.Group.objects.latest('pk')
        user = models.User.objects.latest('pk')
        user.groups.add(self.group)
        user.email = "example@example.com"
        user.save()

        self.recipients = RecipientGroup.objects.create(name="test group")
        self.recipients.groups.add(self.group)

        self.inactive_user = models.User.objects.create_user('inactive', 'inactive@user.com', 'password')
        self.inactive_user.groups.add(self.group)
        self.inactive_user.is_active = False
        self.inactive_user.save()

        self.notice = QCReviewNotice.objects.create(
            recipients=self.recipients,
            notification_type=QCReviewNotice.UNREVIEWED,
            time="0:00",
        )
        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

    def test_send_notice(self):
        self.tli1 = utils.create_test_list_instance(unit_test_collection=self.utc1)
        self.tli1.all_reviewed = False
        self.tli1.save()
        now = timezone.now()
        tasks.send_qcreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent >= now
        assert "QATrack+ Unreviewed QC Notice:" in mail.outbox[0].subject

    def test_send_notice_empty(self):
        self.notice.send_empty = True
        self.notice.save()
        now = timezone.now()
        tasks.send_qcreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent >= now
        assert "QATrack+ Unreviewed QC Notice:" in mail.outbox[0].subject

    def test_send_notice_not_empty(self):
        tasks.send_qcreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert len(mail.outbox) == 0

    def test_send_notice_non_existent(self):
        tasks.send_qcreview_notice(self.notice.pk + 1)
        self.notice.refresh_from_db()
        assert self.notice.last_sent is None
        assert len(mail.outbox) == 0

    def test_send_notice_no_recipients(self):
        utils.create_test_list_instance()
        self.recipients.groups.clear()
        tasks.send_qcreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent is None
        assert len(mail.outbox) == 0

    def test_review_notice(self):
        next_run = timezone.now() + timezone.timedelta(hours=1)
        tasks.schedule_qcreview_notice(self.notice, next_run)
        assert Schedule.objects.count() == 1

    def test_run_review_notices(self):

        self.notice.recurrences = recurrence.Recurrence(rrules=[recurrence.Rule(recurrence.DAILY)])
        self.notice.time = (timezone.localtime(timezone.now()) + timezone.timedelta(minutes=1)).time()
        self.notice.save()
        tasks.run_review_notices()
        assert Schedule.objects.count() == 1
