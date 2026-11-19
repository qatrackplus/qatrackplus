"""Tests for the claim that stops a scheduled email being sent twice (issue #919)."""

from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from qatrack.qa.tests import utils
from qatrack.qatrack_core.models import (
    DELIVERY_RECORD_DAYS,
    ScheduledDelivery,
    claim_lifetime,
)

OCCURRENCE = "Send notification 1 2026-11-19T08:00:00-05:00"


class TestScheduledDeliveryClaim(TestCase):

    def setUp(self):
        # Any saved model will do as the thing the email belongs to.
        self.unit = utils.create_unit()

    def test_first_copy_claims(self):
        assert ScheduledDelivery.claim(self.unit, OCCURRENCE) is not None

    def test_second_copy_cannot_claim_while_first_is_sending(self):
        ScheduledDelivery.claim(self.unit, OCCURRENCE)
        assert ScheduledDelivery.claim(self.unit, OCCURRENCE) is None

    def test_cannot_claim_once_sent(self):
        ScheduledDelivery.claim(self.unit, OCCURRENCE).finish(sent=True)
        assert ScheduledDelivery.claim(self.unit, OCCURRENCE) is None

    def test_failed_send_releases_claim(self):
        ScheduledDelivery.claim(self.unit, OCCURRENCE).finish(sent=False)
        assert ScheduledDelivery.claim(self.unit, OCCURRENCE) is not None

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
        assert ScheduledDelivery.claim(self.unit, OCCURRENCE) is None

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
            "Send notification 1 2026-12-25T08:00:00-05:00",
        ]


class TestClaimLifetime:

    @override_settings(Q_CLUSTER={'timeout': 300, 'retry': 360})
    def test_uses_task_timeout(self):
        assert claim_lifetime() == timezone.timedelta(seconds=300)

    @override_settings(Q_CLUSTER={'retry': 360})
    def test_falls_back_to_retry(self):
        assert claim_lifetime() == timezone.timedelta(seconds=360)

    @override_settings(Q_CLUSTER={})
    def test_falls_back_to_an_hour(self):
        assert claim_lifetime() == timezone.timedelta(hours=1)
