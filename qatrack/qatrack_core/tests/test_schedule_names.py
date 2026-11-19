"""Names of the one-off django-q schedules that send reports and notices.

Every 15 minutes `run_periodic_scheduler` finds the reports and notices due in
the next window and creates a one-off `Schedule` for each one. django-q2 refuses
to create a schedule whose name is already taken (it raises `IntegrityError`), so
the names have to be unique for every distinct send.

They used to be built from the primary key and the send time alone. A QC
Scheduling notice and a QC Review notice that both had primary key 1 and were
both due at 08:00 therefore asked for the same name, and the second one was
never sent. Because that error escaped the scheduling loop, every other notice
of that type due in the same 15 minutes was skipped along with it.
"""

import ast
import logging
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core import mail
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule

from qatrack.notifications.faults_review import tasks as faults_review_tasks
from qatrack.notifications.models import (
    FaultsReviewNotice,
    QCReviewNotice,
    QCSchedulingNotice,
    RecipientGroup,
    ServiceEventReviewNotice,
    ServiceEventSchedulingNotice,
)
from qatrack.notifications.qcreview import tasks as qcreview_tasks
from qatrack.notifications.qcscheduling import tasks as qcscheduling_tasks
from qatrack.notifications.service_log_review import (
    tasks as service_log_review_tasks,
)
from qatrack.notifications.service_log_scheduling import (
    tasks as service_log_scheduling_tasks,
)
from qatrack.qatrack_core.tasks import run_periodic_scheduler
from qatrack.reports import models as report_models
from qatrack.reports import qc
from qatrack.reports import tasks as report_tasks

NOTICE_SCHEDULERS = [
    (QCSchedulingNotice, qcscheduling_tasks.schedule_scheduling_notice),
    (QCReviewNotice, qcreview_tasks.schedule_qcreview_notice),
    (FaultsReviewNotice, faults_review_tasks.schedule_faultsreview_notice),
    (ServiceEventReviewNotice, service_log_review_tasks.schedule_serviceeventreview_notice),
    (ServiceEventSchedulingNotice, service_log_scheduling_tasks.schedule_service_event_scheduling_notice),
]


class TestNoticeScheduleNames(TestCase):
    def setUp(self):
        Schedule.objects.all().delete()
        self.send_time = timezone.now().replace(microsecond=0) + timezone.timedelta(hours=1)

    def test_notices_of_different_types_with_the_same_pk_do_not_collide(self):
        """One notice of each type, all with pk 1 and all due at the same time, each get a schedule."""
        for model, scheduler in NOTICE_SCHEDULERS:
            scheduler(model(pk=1), self.send_time)

        assert Schedule.objects.count() == len(NOTICE_SCHEDULERS)
        assert Schedule.objects.values('name').distinct().count() == len(NOTICE_SCHEDULERS)

    def test_the_same_notice_at_the_same_time_is_still_refused(self):
        """The name is still the guard against queueing one send twice."""
        notice = QCSchedulingNotice(pk=1)
        qcscheduling_tasks.schedule_scheduling_notice(notice, self.send_time)
        with self.assertRaises(IntegrityError):
            qcscheduling_tasks.schedule_scheduling_notice(notice, self.send_time)
        assert Schedule.objects.count() == 1

    def test_the_name_is_passed_through_as_task_name(self):
        """send_* deletes the schedule by the name it is handed, so the two must match."""
        for model, scheduler in NOTICE_SCHEDULERS:
            scheduler(model(pk=1), self.send_time)

        for sch in Schedule.objects.all():
            # django-q stores kwargs as the repr of a dict
            assert ast.literal_eval(sch.kwargs) == {'task_name': sch.name}

    def test_longest_name_fits_the_schedule_name_field(self):
        """Schedule.name holds 100 characters; schedule() validates it and would refuse a longer one."""
        send_time = timezone.now().replace(microsecond=123456)
        service_log_scheduling_tasks.schedule_service_event_scheduling_notice(
            ServiceEventSchedulingNotice(pk=2**31 - 1),
            send_time,
        )
        report_tasks.schedule_report(report_models.ReportSchedule(pk=2**31 - 1, report_id=2**31 - 1), send_time)
        assert Schedule.objects.count() == 2


class TestReportScheduleNames(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('user', 'a@b.com', 'password')
        self.report = report_models.SavedReport.objects.create(
            report_type=qc.TestListInstanceSummaryReport.report_type,
            report_format='pdf',
            title='title',
            filters={'work_completed': ['2 Jan 1989', '4 Jan 1990']},
            created_by=self.user,
            modified_by=self.user,
        )
        Schedule.objects.all().delete()
        self.send_time = timezone.now().replace(microsecond=0) + timezone.timedelta(hours=1)

    def _report_schedule(self):
        return report_models.ReportSchedule.objects.create(
            report=self.report,
            time='00:00',
            schedule='RRULE:FREQ=DAILY',
            created_by=self.user,
            modified_by=self.user,
        )

    def test_replacing_a_report_schedule_does_not_collide_with_the_old_one(self):
        """A report can only have one schedule at a time, but it can be deleted and set up again.

        The old schedule's one-off send is still queued when that happens (and is kept after it runs
        unless the send succeeds), so naming the send after the report rather than the schedule made
        the new schedule's send collide with it.
        """
        old = self._report_schedule()
        report_tasks.schedule_report(old, self.send_time)
        old.delete()

        new = self._report_schedule()
        report_tasks.schedule_report(new, self.send_time)

        assert Schedule.objects.count() == 2
        assert Schedule.objects.values('name').distinct().count() == 2


class TestSendWithScheduleQueuedUnderOldName(TestCase):
    """Schedules created before the upgrade carry the old names, and send_* must still clean them up."""

    def setUp(self):
        group = Group.objects.create(name='group')
        user = User.objects.create_user('user', 'user@example.com', 'password')
        user.groups.add(group)
        recipients = RecipientGroup.objects.create(name='recipients')
        recipients.groups.add(group)
        self.notice = QCSchedulingNotice.objects.create(
            recipients=recipients,
            recurrences='RRULE:FREQ=DAILY',
            notification_type=QCSchedulingNotice.UPCOMING_AND_DUE,
            future_days=7,
            time='0:00',
            send_empty=True,
        )
        Schedule.objects.all().delete()

    def test_old_name_is_deleted_after_a_successful_send(self):
        old_name = 'Send notification %d %s' % (self.notice.pk, timezone.now().isoformat())
        Schedule.objects.create(
            name=old_name,
            func='qatrack.notifications.qcscheduling.tasks.send_scheduling_notice',
            schedule_type=Schedule.ONCE,
            repeats=1,
        )

        qcscheduling_tasks.send_scheduling_notice(self.notice.pk, task_name=old_name)

        assert len(mail.outbox) == 1
        assert not Schedule.objects.filter(name=old_name).exists()


class TestRunPeriodicSchedulerIsolatesFailures(TestCase):
    def setUp(self):
        recipients = RecipientGroup.objects.create(name='recipients')
        due = (timezone.localtime(timezone.now()) + timezone.timedelta(minutes=1)).time()
        self.notices = [
            QCSchedulingNotice.objects.create(
                recipients=recipients,
                recurrences='RRULE:FREQ=DAILY',
                notification_type=QCSchedulingNotice.UPCOMING_AND_DUE,
                future_days=7,
                time=due,
            )
            for __ in range(3)
        ]

    def test_one_failing_handler_does_not_stop_the_rest(self):
        """A handler that raises for one instance is logged, and the remaining instances are still handled."""
        handled = []

        def handler(instance, send_time):
            handled.append(instance.pk)
            if len(handled) == 1:
                raise IntegrityError('A schedule with the same name already exists.')

        with self.assertLogs('django-q2', level=logging.ERROR) as logs:
            run_periodic_scheduler(QCSchedulingNotice, 'test', handler, recurrence_field='recurrences')

        assert sorted(handled) == sorted(n.pk for n in self.notices)
        errors = [r for r in logs.records if r.levelno >= logging.ERROR]
        assert len(errors) == 1
        assert errors[0].exc_info is not None

    def test_a_failing_handler_does_not_break_the_transaction_for_the_rest(self):
        """A database error inside one handler is rolled back to a savepoint rather than poisoning the loop."""
        handled = []

        def handler(instance, send_time):
            handled.append(instance.pk)
            if len(handled) == 1:
                first = Schedule.objects.create(name='x', func='f')
                Schedule.objects.create(id=first.id, name='y', func='f')  # duplicate primary key
            Schedule.objects.create(name='ok %d' % instance.pk, func='f')

        with mock.patch.object(logging.getLogger('django-q2'), 'exception'):
            run_periodic_scheduler(QCSchedulingNotice, 'test', handler, recurrence_field='recurrences')

        assert len(handled) == len(self.notices)
        # the failing handler's own writes are undone; the others' are kept
        assert not Schedule.objects.filter(name__in=['x', 'y']).exists()
        assert Schedule.objects.filter(name__startswith='ok ').count() == len(self.notices) - 1


class TestPeriodicRunsOfDifferentNoticeTypes(TestCase):
    """The way the collision shows up on a real site: two notice types, the same pk, the same time."""

    def test_qc_review_notice_is_scheduled_alongside_a_qc_scheduling_notice(self):
        recipients = RecipientGroup.objects.create(name='recipients')
        due = (timezone.localtime(timezone.now()) + timezone.timedelta(minutes=1)).time()
        notices = [
            QCSchedulingNotice(
                pk=1,
                recipients=recipients,
                recurrences='RRULE:FREQ=DAILY',
                notification_type=QCSchedulingNotice.UPCOMING_AND_DUE,
                future_days=7,
                time=due,
            ),
            QCReviewNotice(
                pk=1,
                recipients=recipients,
                recurrences='RRULE:FREQ=DAILY',
                notification_type=QCReviewNotice.UNREVIEWED,
                time=due,
            ),
        ]
        for notice in notices:
            # save() only sets the recurrence start for a new object without a pk
            notice.relocalize_recurrence()
            notice.save()
        Schedule.objects.all().delete()

        qcscheduling_tasks.run_scheduling_notices()
        qcreview_tasks.run_review_notices()

        funcs = set(Schedule.objects.values_list('func', flat=True))
        assert funcs == {
            'qatrack.notifications.qcscheduling.tasks.send_scheduling_notice',
            'qatrack.notifications.qcreview.tasks.send_qcreview_notice',
        }
