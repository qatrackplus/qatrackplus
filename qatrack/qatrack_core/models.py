import logging

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger('django-q2')

# How long a delivery record is kept after it is created. Records only need to
# outlive any copy of their task that could still be waiting in the queue, so
# a month is generous.
DELIVERY_RECORD_DAYS = 30

# How much longer than django-q's `timeout` a claim holds. django-q2 doesn't
# always stop a worker the moment `timeout` runs out: on Windows, which has no
# SIGALRM, its guard process stops the worker a few seconds later (it adds 3
# seconds and checks every half second). A minute covers that comfortably.
CLAIM_MARGIN_SECONDS = 60


def claim_lifetime():
    """How long a claim on a delivery holds before another copy may take it over.

    A copy that claims a delivery and is then stopped by django-q's `timeout`
    never gets the chance to release its claim. Shortly after `timeout` has
    passed the claiming copy is no longer running, so once `timeout` plus a
    margin (CLAIM_MARGIN_SECONDS) has passed its claim can be treated as
    abandoned. Without a timeout there is no such guarantee, so fall back to
    the broker's `retry` lease, and then to an hour. django-q2 treats a timeout
    of None or a negative number as no timeout at all, so only a positive
    timeout is used. (A timeout of 0 is set aside too; falling back to the
    longer `retry` lease is the safe choice either way.)
    """
    q_cluster = getattr(settings, 'Q_CLUSTER', {})
    timeout = q_cluster.get('timeout')
    retry = q_cluster.get('retry')
    if timeout and timeout > 0:
        seconds = timeout + CLAIM_MARGIN_SECONDS
    elif retry and retry > 0:
        seconds = retry
    else:
        seconds = 60 * 60
    return timezone.timedelta(seconds=seconds)


def occurrence_from_task_name(task_name):
    """The due time a scheduled task's name ends with, e.g. 2026-11-19T08:00:00-05:00.

    Task names have changed (notices now include their type, and reports
    their schedule rather than the report), so a send queued before an upgrade
    and one queued after it can carry different names for the same due time.
    Keying the claim on the due time alone means both claim the same
    occurrence. A name that doesn't end in a date and time is used whole.
    """
    candidate = task_name.rsplit(' ', 1)[-1]
    try:
        return timezone.datetime.fromisoformat(candidate).isoformat()
    except ValueError:
        return task_name


class DeliveryInProgress(Exception):
    """Another copy of this task is sending the email right now.

    Raised rather than returning normally because django-q2 acknowledges a task
    that returns, which deletes it from the queue. Both copies of a redelivered
    task share one queue entry, so if this copy acknowledged it and the copy
    holding the claim were then stopped before it sent, nothing would be left to
    retry and the email would never go. A task that raises is left in the queue
    (QATrack+ doesn't set `ack_failures`), and is handed out again once the
    broker's `retry` lease runs out. By then the claim has been either finished
    or abandoned.
    """


class ScheduledDelivery(models.Model):
    """One scheduled occurrence of an email: a report or notice at one due time.

    django-q can hand the same scheduled task to the cluster more than once,
    for example when the queue backs up past the broker's `retry` lease
    (issue #919). Each copy claims this row before sending, and only the copy
    whose claim succeeds sends the email. The row is marked sent only after
    delivery succeeds, so a send that fails can still be retried.
    """

    # The model the email belongs to (e.g. reports.reportschedule) and its pk.
    kind = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField()
    # The due time, taken from the end of the scheduled task's name (see
    # occurrence_from_task_name). Paired with kind and object_id it identifies
    # one occurrence.
    occurrence = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['kind', 'object_id', 'occurrence'],
                name='qatrack_core_scheduleddelivery_unique_occurrence',
            ),
        ]

    def __str__(self):
        return '%s %s %s' % (self.kind, self.object_id, self.occurrence)

    @classmethod
    def claim(cls, instance, task_name, occurrence=None):
        """Claim the right to send `instance`'s email for the task `task_name`.

        The occurrence is normally the due time at the end of `task_name`.
        Pass `occurrence` to key the claim on something else, for a sender
        whose instance can have more than one email due at the same time
        (a QC Completed follow-up, one per test list instance).

        Returns a `DeliveryClaim` if this copy should send, or None if the
        email has already been sent. Raises `DeliveryInProgress` if another
        copy is sending it right now.
        """

        if not task_name:
            # Called by hand rather than from a schedule, so there is no
            # occurrence to guard. Send as before.
            return DeliveryClaim(None, None)

        delivery, created = cls.objects.get_or_create(
            kind=instance._meta.label_lower,
            object_id=instance.pk,
            occurrence=occurrence or occurrence_from_task_name(task_name),
        )
        if created:
            cls.prune()

        now = timezone.now()
        claimable = Q(claimed_at__isnull=True) | Q(claimed_at__lt=now - claim_lifetime())

        # A single conditional UPDATE is atomic on every database we support,
        # so when two copies race only one of them changes the row.
        won = cls.objects.filter(
            claimable,
            pk=delivery.pk,
            sent_at__isnull=True,
        ).update(claimed_at=now)

        if won:
            return DeliveryClaim(delivery.pk, now)

        if cls.objects.filter(pk=delivery.pk, sent_at__isnull=False).exists():
            return None

        raise DeliveryInProgress(
            "%s %s (%s) is being sent by another worker; leaving this copy in the queue to retry later" % (
                instance._meta.object_name, instance.pk, task_name,
            )
        )

    @classmethod
    def prune(cls):
        cutoff = timezone.now() - timezone.timedelta(days=DELIVERY_RECORD_DAYS)
        cls.objects.filter(created__lt=cutoff).delete()


class DeliveryClaim:
    """The claim a copy of a task holds on a `ScheduledDelivery` while it sends."""

    def __init__(self, delivery_id, claimed_at):
        self.delivery_id = delivery_id
        self.claimed_at = claimed_at

    def finish(self, sent):
        """Mark the delivery sent, or release the claim so a retry can send it."""

        if self.delivery_id is None:
            return

        # Filtering on our own claim time means a copy whose claim was taken
        # over after it expired can't overwrite the newer copy's claim.
        mine = ScheduledDelivery.objects.filter(pk=self.delivery_id, claimed_at=self.claimed_at)
        if sent:
            mine.update(sent_at=timezone.now())
        else:
            mine.update(claimed_at=None)
