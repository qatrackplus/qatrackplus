from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule
import recurrence

from qatrack.notifications.models import (
    RecipientGroup,
    ServiceEventReviewNotice,
    UnitGroup,
)
from qatrack.notifications.service_log_review import admin, tasks
from qatrack.qa import models
import qatrack.qa.tests.utils as qa_utils
import qatrack.service_log.tests.utils as utils
import qatrack.units.tests.utils as u_utils


class TestServiceEventReviewAdmin(TestCase):

    def setUp(self):
        self.admin = admin.ServiceEventReviewAdmin(model=ServiceEventReviewNotice, admin_site=AdminSite())

    def test_get_notification_type_unreviewed(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = ServiceEventReviewNotice.objects.create(
            notification_type=ServiceEventReviewNotice.UNREVIEWED,
            time="0:00",
            recipients=rg,
        )
        assert "Notify about Service Events awaiting review" in self.admin.get_notification_type(n)

    def test_get_units(self):
        u = u_utils.create_unit(name="Test Unit")
        ug = UnitGroup.objects.create(name="UG")
        ug.units.add(u)
        rg = RecipientGroup.objects.create(name="RG")
        n = ServiceEventReviewNotice.objects.create(
            notification_type=ServiceEventReviewNotice.UNREVIEWED,
            units=ug,
            recipients=rg,
            time="0:00",
        )
        assert ug.name in self.admin.get_units(n)

    def test_get_recipients(self):
        rg = RecipientGroup.objects.create(name="RG")
        n = ServiceEventReviewNotice.objects.create(
            notification_type=ServiceEventReviewNotice.UNREVIEWED,
            recipients=rg,
            time="0:00",
        )
        assert rg.name in self.admin.get_recipients(n)


class TestServiceEventReviewModel(TestCase):

    def setUp(self):

        self.unit1 = u_utils.create_unit(name="unit1", number=1)
        self.unit2 = u_utils.create_unit(name="unit2", number=2)
        self.usa1 = utils.create_unit_service_area(unit=self.unit1)
        self.usa2 = utils.create_unit_service_area(unit=self.unit2)

        self.se1 = utils.create_service_event(unit_service_area=self.usa1, is_review_required=True)
        self.se2 = utils.create_service_event(unit_service_area=self.usa2, is_review_required=False)

        self.unit_group = UnitGroup.objects.create(name="test group")
        self.unit_group.units.add(self.usa1.unit)

        self.group = qa_utils.create_group()
        user = models.User.objects.latest('pk')
        user.is_active = True
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
        self.se1.is_review_required = True
        self.se1.save()
        self.se2.is_review_required = True
        self.se2.save()

        notice = ServiceEventReviewNotice.objects.create(
            recipients=self.recipients,
            notification_type=ServiceEventReviewNotice.UNREVIEWED,
            time="0:00",
        )
        expected = [
            {
                'unit_service_area__unit__name': self.usa1.unit.name,
                'unit_service_area__service_area__name': self.usa1.service_area.name,
                'unit_service_area__unit__name__count': 1,
                'unit_service_area__service_area__name__count': 1,
            },
            {
                'unit_service_area__unit__name': self.usa2.unit.name,
                'unit_service_area__service_area__name': self.usa2.service_area.name,
                'unit_service_area__unit__name__count': 1,
                'unit_service_area__service_area__name__count': 1,
            },
        ]
        assert list(notice.ses_by_unit_usa()) == expected

    def test_upcoming_both_unreviewed_unit_group(self):
        self.se1.is_review_required = True
        self.se1.save()
        self.se2.is_review_required = False
        self.se2.save()

        notice = ServiceEventReviewNotice.objects.create(
            recipients=self.recipients,
            units=self.unit_group,
            notification_type=ServiceEventReviewNotice.UNREVIEWED,
            time="0:00",
        )
        expected = [
            {
                'unit_service_area__unit__name': self.usa1.unit.name,
                'unit_service_area__service_area__name': self.usa1.service_area.name,
                'unit_service_area__unit__name__count': 1,
                'unit_service_area__service_area__name__count': 1,
            },
        ]
        assert list(notice.ses_by_unit_usa()) == expected

    def test_is_props(self):
        assert ServiceEventReviewNotice(notification_type=ServiceEventReviewNotice.UNREVIEWED).is_unreviewed


class TestServiceEventReviewEmails(TestCase):

    def setUp(self):

        self.unit1 = u_utils.create_unit(name="unit1", number=1)
        self.unit2 = u_utils.create_unit(name="unit2", number=2)
        self.usa1 = utils.create_unit_service_area(unit=self.unit1)
        self.usa2 = utils.create_unit_service_area(unit=self.unit2)

        self.unit_group = UnitGroup.objects.create(name="test group")
        self.unit_group.units.add(self.usa1.unit)

        self.group = qa_utils.create_group()
        user = models.User.objects.latest('pk')
        user.groups.add(self.group)
        user.is_active = True
        user.email = "example@example.com"
        user.save()

        self.recipients = RecipientGroup.objects.create(name="test group")
        self.recipients.groups.add(self.group)

        self.inactive_user = models.User.objects.create_user('inactive', 'inactive@user.com', 'password')
        self.inactive_user.groups.add(self.group)
        self.inactive_user.is_active = False
        self.inactive_user.save()

        self.notice = ServiceEventReviewNotice.objects.create(
            recipients=self.recipients,
            notification_type=ServiceEventReviewNotice.UNREVIEWED,
            time="0:00",
        )
        # delete defaults schedules to make counting easier
        Schedule.objects.all().delete()

    def test_send_notice(self):
        self.se1 = utils.create_service_event(unit_service_area=self.usa1)
        self.se1.is_review_required = True
        self.se1.save()
        now = timezone.now()
        tasks.send_serviceeventreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent >= now
        assert "QATrack+ Unreviewed Service Event Notice:" in mail.outbox[0].subject

    def test_send_notice_empty(self):
        self.notice.send_empty = True
        self.notice.save()
        now = timezone.now()
        tasks.send_serviceeventreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent >= now
        assert "QATrack+ Unreviewed Service Event Notice:" in mail.outbox[0].subject

    def test_send_notice_not_empty(self):
        tasks.send_serviceeventreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert len(mail.outbox) == 0

    def test_send_notice_non_existent(self):
        tasks.send_serviceeventreview_notice(self.notice.pk + 1)
        self.notice.refresh_from_db()
        assert self.notice.last_sent is None
        assert len(mail.outbox) == 0

    def test_send_notice_no_recipients(self):
        utils.create_service_event(is_review_required=True)
        self.recipients.groups.clear()
        tasks.send_serviceeventreview_notice(self.notice.pk)
        self.notice.refresh_from_db()
        assert self.notice.last_sent is None
        assert len(mail.outbox) == 0

    def test_review_notice(self):
        next_run = timezone.now() + timezone.timedelta(hours=1)
        tasks.schedule_serviceeventreview_notice(self.notice, next_run)
        assert Schedule.objects.count() == 1

    def test_run_review_notices(self):

        self.notice.recurrences = recurrence.Recurrence(rrules=[recurrence.Rule(recurrence.DAILY)])
        self.notice.time = (timezone.localtime(timezone.now()) + timezone.timedelta(minutes=1)).time()
        self.notice.save()
        tasks.run_service_event_review_notices()
        assert Schedule.objects.count() == 1
