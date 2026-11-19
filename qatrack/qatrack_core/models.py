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


def claim_lifetime():
    """How long a claim on a delivery holds before another copy may take it over.

    A copy that claims a delivery and is then stopped by django-q's `timeout`
    never gets the chance to release its claim. Once `timeout` has passed the
    claiming copy is certainly no longer running, so its claim can be treated
    as abandoned. Without a timeout there is no such guarantee, so fall back to
    the broker's `retry` lease, and then to an hour.
    """
    q_cluster = getattr(settings, 'Q_CLUSTER', {})
    seconds = q_cluster.get('timeout') or q_cluster.get('retry') or 60 * 60
    return timezone.timedelta(seconds=seconds)


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
    # The scheduled task's name, which includes the due time. Paired with kind
    # and object_id it identifies one occurrence: notice task names on their
    # own are not unique across notice types.
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
    def claim(cls, instance, occurrence):
        """Claim the right to send `instance`'s email for `occurrence`.

        Returns a `DeliveryClaim` if this copy should send, or None if the
        email has already been sent, or another copy is sending it right now.
        """

        if not occurrence:
            # Called by hand rather than from a schedule, so there is no
            # occurrence to guard. Send as before.
            return DeliveryClaim(None, None)

        delivery, created = cls.objects.get_or_create(
            kind=instance._meta.label_lower,
            object_id=instance.pk,
            occurrence=occurrence,
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

        if not won:
            return None

        return DeliveryClaim(delivery.pk, now)

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
