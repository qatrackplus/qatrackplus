from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule
import recurrence

from qatrack.notifications.models import (
    QCSchedulingNotice,
    RecipientGroup,
    TestListGroup,
    UnitGroup,
)
from qatrack.notifications.qcscheduling import admin, tasks
from qatrack.qa import models
import qatrack.qa.tests.utils as utils
from qatrack.qatrack_core.utils import today_start_end


class TestQCSchedulingAdmin(TestCase):

    def setUp(self):
        self.admin = admin.QCSchedulingAdmin(model=QCSchedulingNotice, admin_site=AdminSite())

    def test_clean_missing_future_days_upcoming(self):
        f = admin.QCSchedulingNoticeAdminForm()
        f.cleaned_data = {'notification_type': QCSchedulingNotice.UPCOMING}
        f.clean()
        assert 'future_days' in f.errors

    def test_clean_missing_future_days_upcoming_and_due(self):
        f = admin.QCSchedulingNoticeAdminForm()
        f.cleaned_data = {'notification_type': QCSchedulingNotice.UPCOMING_AND_DUE}
        f.clean()
        assert 'future_days' in f.errors

    def test_clean_future_days_not_required(self):
        f = admin.QCSchedulingNoticeAdminForm()
        f.cleaned_data = {'notification_type': QCSchedulingNotice.DUE, 'future_days': 10}
        f.clean()
        assert 'future_days' in f.errors

    def test_clean_ok(self):
        f = admin.QCSchedulingNoticeAdminForm()
        f.cleaned_data = {'notification_type': QCSchedulingNotice.UPCOMING_AND_DUE, 'future_days': 10}
        f.clean()
        assert not f.errors

    def test_get_notification_type_upcoming(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = QCSchedulingNotice.objects.create(
            notification_type=QCSchedulingNotice.UPCOMING,
            future_days=1,
            time="0:00",
            recipients=rg,
        )
        assert "Upcoming Due Dates Only" in self.admin.get_notification_type(n)

    def test_get_notification_type_upcoming_and_due(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = QCSchedulingNotice.objects.create(
            notification_type=QCSchedulingNotice.UPCOMING_AND_DUE,
            future_days=1,
            time="0:00",
            recipients=rg,
        )
        assert "Notify About Test Lists Currently Due & Overdue, and Upcoming" in self.admin.get_notification_type(n)

    def test_get_notification_type_due(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = QCSchedulingNotice.objects.create(
            notification_type=QCSchedulingNotice.DUE,
            time="0:00",
            recipients=rg,
        )
        assert n.get_notification_type_display() in self.admin.get_notification_type(n)

    def test_get_units(self):
        u = utils.create_unit(name="Test Unit")
        ug = UnitGroup.objects.create(name="UG")
        ug.units.add(u)
        rg = RecipientGroup.objects.create(name="RG")
        n = QCSchedulingNotice.objects.create(
            notification_type=QCSchedulingNotice.DUE,
            units=ug,
            recipients=rg,
            time="0:00",
        )
        assert ug.name in self.admin.get_units(n)

    def test_get_recipients(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = QCSchedulingNotice.objects.create(
            notification_type=QCSchedulingNotice.DUE,
            recipients=rg,
            time="0:00",
        )
        assert rg.name in self.admin.get_recipients(n)

    def test_get_testlists(self):
        tl = utils.create_test_list(name="TL")
        rg = RecipientGroup.objects.create(name="RG")
        tlg = TestListGroup.objects.create(name="TLG")
        tlg.test_lists.add(tl)
        n = QCSchedulingNotice.objects.create(
            notification_type=QCSchedulingNotice.DUE,
            recipients=rg,
            test_lists=tlg,
            time="0:00",
        )
        assert tlg.name in self.admin.get_testlists(n)


class TestQCSchedulingModel(TestCase):

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

        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

    def test_upcoming_both_overdue_no_groups(self):
        self.utc1.due_date = timezone.now() + timezone.timedelta(hours=24)
        self.utc1.save()
        self.utc2.due_date = timezone.now() + timezone.timedelta(hours=2 * 24)
        self.utc2.save()

        notice = QCSchedulingNotice.objects.create(
            future_days=7,
            recipients=self.recipients,
            notification_type=QCSchedulingNotice.UPCOMING,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [self.utc1, self.utc2]

    def test_upcoming_one_overdue_no_groups(self):
        self.utc1.due_date = timezone.now() + timezone.timedelta(hours=24)
        self.utc1.save()
        self.utc2.due_date = timezone.now() + timezone.timedelta(hours=2 * 24)
        self.utc2.save()

        notice = QCSchedulingNotice.objects.create(
            future_days=1,
            recipients=self.recipients,
            notification_type=QCSchedulingNotice.UPCOMING,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [self.utc1]

    def test_upcoming_both_overdue_unit_group(self):
        self.utc1.due_date = timezone.now() + timezone.timedelta(hours=24)
        self.utc1.save()
        self.utc2.due_date = timezone.now() + timezone.timedelta(hours=2 * 24)
        self.utc2.save()

        notice = QCSchedulingNotice.objects.create(
            future_days=7,
            recipients=self.recipients,
            units=self.unit_group,
            notification_type=QCSchedulingNotice.UPCOMING,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [self.utc1]

    def test_upcoming_both_overdue_testlist_group(self):
        self.utc1.due_date = timezone.now() + timezone.timedelta(hours=24)
        self.utc1.save()
        self.utc2.due_date = timezone.now() + timezone.timedelta(hours=2 * 24)
        self.utc2.save()

        notice = QCSchedulingNotice.objects.create(
            future_days=7,
            recipients=self.recipients,
            test_lists=self.testlist_group,
            notification_type=QCSchedulingNotice.UPCOMING,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [self.utc1]

    def test_upcoming_both_overdue_testlist_group_unit_group(self):
        self.utc1.due_date = timezone.now() + timezone.timedelta(hours=24)
        self.utc1.save()
        self.utc2.due_date = timezone.now() + timezone.timedelta(hours=2 * 24)
        self.utc2.save()

        notice = QCSchedulingNotice.objects.create(
            future_days=7,
            recipients=self.recipients,
            test_lists=self.testlist_group,
            units=self.unit_group,
            notification_type=QCSchedulingNotice.UPCOMING,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [self.utc1]

    def test_upcoming_cycle_due_testlist_group(self):
        tl = self.utc2.tests_object
        tlc = utils.create_cycle(test_lists=[tl])
        utc = utils.create_unit_test_collection(unit=self.utc1.unit, test_collection=tlc)
        utc.due_date = timezone.now() + timezone.timedelta(hours=24)
        utc.save()

        tlg = TestListGroup.objects.create(name="test group for cycle")
        tlg.test_lists.add(tl)
        notice = QCSchedulingNotice.objects.create(
            future_days=7,
            recipients=self.recipients,
            test_lists=tlg,
            notification_type=QCSchedulingNotice.UPCOMING,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [utc]

    def test_all(self):
        start, end = today_start_end()
        self.utc1.due_date = start + timezone.timedelta(hours=12)
        self.utc1.save()
        self.utc2.due_date = timezone.now() + timezone.timedelta(hours=2 * 24)
        self.utc2.save()

        notice = QCSchedulingNotice.objects.create(
            recipients=self.recipients,
            notification_type=QCSchedulingNotice.ALL,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [self.utc1, self.utc2]

    def test_due(self):
        start, end = today_start_end()
        self.utc1.due_date = start + timezone.timedelta(hours=12)
        self.utc1.save()
        self.utc2.due_date = timezone.now() + timezone.timedelta(hours=2 * 24)
        self.utc2.save()

        notice = QCSchedulingNotice.objects.create(
            recipients=self.recipients,
            notification_type=QCSchedulingNotice.DUE,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [self.utc1]

    def test_due_and_overdue(self):
        start, end = today_start_end()
        self.utc1.due_date = start + timezone.timedelta(hours=12)
        self.utc1.save()
        self.utc2.due_date = timezone.now() - timezone.timedelta(hours=2 * 24)
        self.utc2.save()

        notice = QCSchedulingNotice.objects.create(
            recipients=self.recipients,
            notification_type=QCSchedulingNotice.DUE,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [self.utc1, self.utc2]

    def test_upcoming_and_overdue(self):
        start, end = today_start_end()
        self.utc1.due_date = start + timezone.timedelta(hours=36)
        self.utc1.save()
        self.utc2.due_date = timezone.now() - timezone.timedelta(hours=2 * 24)
        self.utc2.save()

        notice = QCSchedulingNotice.objects.create(
            recipients=self.recipients,
            notification_type=QCSchedulingNotice.UPCOMING_AND_DUE,
            future_days=7,
            time="0:00",
        )
        assert list(notice.utcs_to_notify()) == [self.utc1, self.utc2]

    def test_is_props(self):
        assert QCSchedulingNotice(notification_type=QCSchedulingNotice.ALL).is_all
        assert QCSchedulingNotice(notification_type=QCSchedulingNotice.DUE).is_due
        assert QCSchedulingNotice(notification_type=QCSchedulingNotice.UPCOMING).is_upcoming
        assert QCSchedulingNotice(notification_type=QCSchedulingNotice.UPCOMING_AND_DUE).is_upcoming_and_due


class TestQCSchedulingEmails(TestCase):

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

        self.notice = QCSchedulingNotice.objects.create(
            recipients=self.recipients,
            notification_type=QCSchedulingNotice.UPCOMING_AND_DUE,
            future_days=7,
            time="0:00",
        )
        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

    def test_send_notice_send_empty(self):
        now = timezone.now()
        self.notice.send_empty = True
        self.notice.save()
        tasks.send_scheduling_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent >= now
        assert "QATrack+ QC Scheduling Notice:" in mail.outbox[0].subject

    def test_send_notice_no_send_empty(self):
        tasks.send_scheduling_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert len(mail.outbox) == 0

    def test_send_notice_non_existent(self):
        tasks.send_scheduling_notice(self.notice.pk + 1)
        self.notice.refresh_from_db()
        assert self.notice.last_sent is None
        assert len(mail.outbox) == 0

    def test_send_notice_no_recipients(self):
        utils.create_test_list_instance()
        self.recipients.groups.clear()
        tasks.send_scheduling_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent is None
        assert len(mail.outbox) == 0

    def test_schedule_notice(self):
        next_run = timezone.now() + timezone.timedelta(hours=1)
        tasks.schedule_scheduling_notice(self.notice, next_run)
        assert Schedule.objects.count() == 1

    def test_run_scheduling_notices(self):

        self.notice.recurrences = recurrence.Recurrence(rrules=[recurrence.Rule(recurrence.DAILY)])
        self.notice.time = (timezone.localtime(timezone.now()) + timezone.timedelta(minutes=1)).time()
        self.notice.save()
        tasks.run_scheduling_notices()
        assert Schedule.objects.count() == 1
