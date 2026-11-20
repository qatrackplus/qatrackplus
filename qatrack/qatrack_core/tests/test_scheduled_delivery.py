"""Tests for the claim that stops a scheduled email being sent twice (issue #919)."""

import queue
import uuid
from multiprocessing import Value
from unittest import mock

import pytest
from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django_q import monitor as q_monitor
from django_q import worker as q_worker
from django_q.brokers import get_broker
from django_q.conf import Conf
from django_q.models import OrmQ

from qatrack.notifications.models import QCSchedulingNotice, RecipientGroup
from qatrack.qa.tests import utils
from qatrack.qatrack_core.models import (
    CLAIM_MARGIN_SECONDS,
    DELIVERY_RECORD_DAYS,
    NO_TIMEOUT_CLAIM_SECONDS,
    DeliveryInProgress,
    ScheduledDelivery,
    claim_lifetime,
    occurrence_from_task_name,
)

OCCURRENCE = "Send notification 1 2026-11-19T08:00:00-05:00"


class TestScheduledDeliveryClaim(TestCase):

    def setUp(self):
        # Any saved model will do as the thing the email belongs to.
        self.unit = utils.create_unit()

    def test_first_copy_claims(self):
        assert ScheduledDelivery.claim(self.unit, OCCURRENCE) is not None

    def test_second_copy_cannot_claim_while_first_is_sending(self):
        """It raises rather than returning, so django-q leaves the task queued (see TestDuplicateStaysQueued)"""
        ScheduledDelivery.claim(self.unit, OCCURRENCE)
        with pytest.raises(DeliveryInProgress):
            ScheduledDelivery.claim(self.unit, OCCURRENCE)

    def test_cannot_claim_once_sent(self):
        ScheduledDelivery.claim(self.unit, OCCURRENCE).finish(sent=True)
        assert ScheduledDelivery.claim(self.unit, OCCURRENCE) is None

    def test_failed_send_releases_claim(self):
        ScheduledDelivery.claim(self.unit, OCCURRENCE).finish(sent=False)
        assert ScheduledDelivery.claim(self.unit, OCCURRENCE) is not None

    def test_old_and_new_task_names_claim_the_same_occurrence(self):
        """A send queued under the old task name and one queued under the new name, for the same due time"""
        ScheduledDelivery.claim(self.unit, OCCURRENCE).finish(sent=True)
        renamed = "Send Unit 1 2026-11-19T08:00:00-05:00"
        assert ScheduledDelivery.claim(self.unit, renamed) is None

    def test_different_occurrence_is_independent(self):
        ScheduledDelivery.claim(self.unit, OCCURRENCE).finish(sent=True)
        other = "Send notification 1 2026-11-20T08:00:00-05:00"
        assert ScheduledDelivery.claim(self.unit, other) is not None

    def test_same_task_name_for_another_model_is_independent(self):
        """Notice task names are only unique per notice type, so the model is part of the key"""
        ScheduledDelivery.claim(self.unit, OCCURRENCE).finish(sent=True)
        other_kind = utils.create_frequency()
        other_kind.pk = self.unit.pk
        assert ScheduledDelivery.claim(other_kind, OCCURRENCE) is not None

    def test_abandoned_claim_can_be_taken_over(self):
        """A copy stopped by the task timeout never releases its claim, so it must expire"""
        first = ScheduledDelivery.claim(self.unit, OCCURRENCE)
        expired = timezone.now() - claim_lifetime() - timezone.timedelta(seconds=1)
        ScheduledDelivery.objects.update(claimed_at=expired)
        first.claimed_at = expired

        second = ScheduledDelivery.claim(self.unit, OCCURRENCE)
        assert second is not None

        # The abandoned copy finishing late must not undo the new copy's claim
        first.finish(sent=False)
        with pytest.raises(DeliveryInProgress):
            ScheduledDelivery.claim(self.unit, OCCURRENCE)

        second.finish(sent=True)
        assert ScheduledDelivery.objects.get().sent_at is not None

    def test_no_occurrence_is_not_guarded(self):
        """A send called by hand, with no schedule behind it, sends as before"""
        claim = ScheduledDelivery.claim(self.unit, "")
        assert claim is not None
        assert ScheduledDelivery.claim(self.unit, "") is not None
        claim.finish(sent=True)
        assert not ScheduledDelivery.objects.exists()

    def test_old_records_are_pruned(self):
        ScheduledDelivery.claim(self.unit, OCCURRENCE).finish(sent=True)
        old = timezone.now() - timezone.timedelta(days=DELIVERY_RECORD_DAYS + 1)
        ScheduledDelivery.objects.update(created=old)

        ScheduledDelivery.claim(self.unit, "Send notification 1 2026-12-25T08:00:00-05:00")

        assert list(ScheduledDelivery.objects.values_list('occurrence', flat=True)) == [
            "2026-12-25T08:00:00-05:00",
        ]

    @override_settings(Q_CLUSTER={'timeout': -1, 'retry': 360})
    def test_disabled_timeout_still_blocks_a_second_claim(self):
        """django-q2 reads a timeout of -1 as no timeout, which must not make every claim expire at once"""
        ScheduledDelivery.claim(self.unit, OCCURRENCE)
        with pytest.raises(DeliveryInProgress):
            ScheduledDelivery.claim(self.unit, OCCURRENCE)

    @override_settings(Q_CLUSTER={'timeout': -1, 'retry': 360})
    def test_without_a_timeout_a_slow_send_is_not_taken_over_after_retry(self):
        """With no timeout nothing stops a slow send, so its claim must outlast the `retry` lease"""
        ScheduledDelivery.claim(self.unit, OCCURRENCE)
        # the broker hands the task out again once `retry` has passed, while the first copy is still sending
        ScheduledDelivery.objects.update(claimed_at=timezone.now() - timezone.timedelta(seconds=360 + 1))
        with pytest.raises(DeliveryInProgress):
            ScheduledDelivery.claim(self.unit, OCCURRENCE)


class TestOccurrenceFromTaskName:

    def test_takes_the_due_time_from_the_end_of_the_name(self):
        assert occurrence_from_task_name(OCCURRENCE) == "2026-11-19T08:00:00-05:00"

    def test_old_and_new_names_give_the_same_occurrence(self):
        old = "Send report 7 2026-11-19T08:00:00-05:00"
        new = "Send ReportSchedule 3 2026-11-19T08:00:00-05:00"
        assert occurrence_from_task_name(old) == occurrence_from_task_name(new)

    def test_a_name_without_a_due_time_is_used_whole(self):
        assert occurrence_from_task_name("follow-up-for-tli-4-notice-2") == "follow-up-for-tli-4-notice-2"


class TestClaimLifetime:

    @override_settings(Q_CLUSTER={'timeout': 300, 'retry': 360})
    def test_uses_task_timeout_plus_a_margin(self):
        # django-q2 can stop a timed-out worker a few seconds after `timeout`
        assert claim_lifetime() == timezone.timedelta(seconds=300 + CLAIM_MARGIN_SECONDS)
        assert CLAIM_MARGIN_SECONDS >= 10

    @override_settings(Q_CLUSTER={'retry': 360})
    def test_without_a_timeout_holds_for_an_hour(self):
        assert claim_lifetime() == timezone.timedelta(seconds=NO_TIMEOUT_CLAIM_SECONDS)
        assert NO_TIMEOUT_CLAIM_SECONDS >= 60 * 60

    @override_settings(Q_CLUSTER={'retry': 2 * 60 * 60})
    def test_without_a_timeout_a_longer_retry_is_used(self):
        assert claim_lifetime() == timezone.timedelta(hours=2)

    @override_settings(Q_CLUSTER={})
    def test_falls_back_to_an_hour(self):
        assert claim_lifetime() == timezone.timedelta(hours=1)

    @pytest.mark.parametrize('timeout', [None, 0, -1])
    def test_a_disabled_timeout_holds_for_an_hour(self, timeout):
        with override_settings(Q_CLUSTER={'timeout': timeout, 'retry': 360}):
            assert claim_lifetime() == timezone.timedelta(hours=1)

    @override_settings(Q_CLUSTER={'timeout': -1, 'retry': -1})
    def test_disabled_timeout_and_retry_fall_back_to_an_hour(self):
        assert claim_lifetime() == timezone.timedelta(hours=1)


class TestDuplicateStaysQueued(TestCase):
    """Run copies of a scheduled send through django-q2's own worker and monitor.

    Both copies of a redelivered task share one entry in the ORM broker's
    queue. django-q2 deletes that entry when a copy returns normally, and
    keeps it when a copy fails. So a duplicate that finds the email still
    being sent has to fail. Otherwise, if the copy sending it is then stopped
    before it sends, nothing is left in the queue to retry it.
    """

    func = 'qatrack.notifications.qcscheduling.tasks.send_scheduling_notice'

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
        self.task_name = 'Send QCSchedulingNotice %d 2026-11-19T08:00:00-05:00' % self.notice.pk
        self.broker = get_broker()
        # the queue entry both copies were handed
        self.ack_id = self.broker.enqueue('payload')

    def run_copy(self):
        task = {
            'id': uuid.uuid4().hex,
            'name': self.task_name,
            'func': self.func,
            'args': (self.notice.pk, self.task_name),
            'kwargs': {},
            'started': timezone.now(),
            'ack_id': self.ack_id,
            'timeout': -1,
        }
        task_queue, result_queue = queue.Queue(), queue.Queue()
        task_queue.put(task)
        task_queue.put('STOP')
        # The cluster closes stale connections between tasks, which here would
        # close the test's own transaction.
        with (
            mock.patch.object(q_worker, 'close_old_django_connections'),
            mock.patch.object(q_monitor, 'close_old_django_connections'),
        ):
            q_worker.worker(task_queue, result_queue, Value('f', -1))
            result_queue.put('STOP')
            q_monitor.monitor(result_queue, self.broker)

    def still_queued(self):
        return OrmQ.objects.filter(pk=self.ack_id).exists()

    def test_duplicate_of_a_send_in_progress_stays_queued(self):
        first_copy = ScheduledDelivery.claim(self.notice, self.task_name)

        self.run_copy()

        assert len(mail.outbox) == 0
        assert self.still_queued()

        # The first copy is stopped before it sends; the copy redelivered
        # afterwards sends the email and takes the task off the queue.
        first_copy.finish(sent=False)
        self.run_copy()

        assert len(mail.outbox) == 1
        assert not self.still_queued()

    def test_duplicate_of_a_finished_send_is_taken_off_the_queue(self):
        ScheduledDelivery.claim(self.notice, self.task_name).finish(sent=True)

        self.run_copy()

        assert len(mail.outbox) == 0
        assert not self.still_queued()

    def test_qatrack_leaves_failed_tasks_queued(self):
        """Everything above relies on this django-q2 default; turning on ack_failures would undo it"""
        assert not Conf.ACK_FAILURES
