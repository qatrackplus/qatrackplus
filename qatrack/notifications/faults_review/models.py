from datetime import time as dt_time

from django.conf import settings
from django.db import models
from django.db.models import Count
from django.utils.translation import gettext_lazy as _l
from recurrence.fields import RecurrenceField

from qatrack.faults.models import Fault
from qatrack.notifications.common.models import RecipientGroup, UnitGroup


class FaultsReviewNotice(models.Model):

    UNREVIEWED = 0

    NOTIFICATION_TYPES = ((UNREVIEWED, _l("Notify about Faults awaiting review")),)

    TIME_CHOICES = [(dt_time(x // 60, x % 60), "%02d:%02d" % (x // 60, x % 60)) for x in range(0, 24 * 60, 15)]

    notification_type = models.IntegerField(
        verbose_name=_l("Notification Type"),
        choices=NOTIFICATION_TYPES,
        default=UNREVIEWED,
    )

    send_empty = models.BooleanField(
        verbose_name=_l("Send Empty Notices"),
        help_text=_l("Check to send notices even if there's no unreviewed Service Events to currently notify about"),
        default=False,
    )

    recurrences = RecurrenceField(
        verbose_name=_l("Recurrences"),
        help_text=_l("Define the schedule this notification should be sent on."),
        default="",
    )

    time = models.TimeField(
        verbose_name=_l("Time of day"),
        help_text=_l("Set the time of day this notice should be sent (00:00-23:59)."),
        choices=TIME_CHOICES,
    )

    recipients = models.ForeignKey(
        RecipientGroup,
        verbose_name=_l("Recipients"),
        help_text=_l("Choose the group of recipients who should receive these notifications"),
        on_delete=models.PROTECT,
    )

    units = models.ForeignKey(
        UnitGroup,
        verbose_name=_l("Unit Group filter"),
        help_text=_l(
            "Select which group of Units this notification should be limited to. Leave blank to include all units"
        ),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    last_sent = models.DateTimeField(null=True, editable=False)

    class Meta:
        verbose_name = _l("Fault Review Notice")

    @property
    def is_unreviewed(self):
        return self.notification_type == self.UNREVIEWED

    def faults(self):
        """Return faults relevant to this notice"""

        faults = Fault.objects.unreviewed()

        if self.units_id:
            faults = faults.filter(unit__in=self.units.units.all())

        return faults.order_by(
            "unit__%s" % settings.ORDER_UNITS_BY,
            "fault_types__code",
        )

    def faults_by_unit_fault_type(self):

        faults = self.faults()
        return faults.values(
            "unit__name",
            "fault_types__code",
        ).order_by(
            "unit__name",
            "fault_types__code",
        ).annotate(
            Count("unit__name"),
            Count("fault_types__code"),
        )

    def send_required(self):
        return self.send_empty or self.faults().count() > 0
