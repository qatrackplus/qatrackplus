from datetime import time as dt_time

from django.conf import settings
from django.db import models
from django.db.models import Count
from django.utils.translation import gettext_lazy as _l
from recurrence.fields import RecurrenceField

from qatrack.notifications.common.models import RecipientGroup, UnitGroup
from qatrack.qatrack_core.scheduling import RecurrenceFieldMixin
from qatrack.service_log.models import ServiceEvent


class ServiceEventReviewNotice(RecurrenceFieldMixin, models.Model):

    UNREVIEWED = 0

    NOTIFICATION_TYPES = ((UNREVIEWED, _l("Notify about Service Events awaiting review")),)

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
        verbose_name = _l("Service Event Review Notice")

    @property
    def is_unreviewed(self):
        return self.notification_type == self.UNREVIEWED

    def ses(self):
        """Return TestListInstances relevant to this notice"""

        ses = ServiceEvent.objects.review_required()

        if self.units_id:
            ses = ses.filter(unit_service_area__unit__in=self.units.units.all())

        return ses.order_by(
            "unit_service_area__unit__%s" % settings.ORDER_UNITS_BY,
            "unit_service_area__service_area__name",
        )

    def ses_by_unit_usa(self):

        ses = self.ses()
        return ses.values(
            "unit_service_area__unit__name",
            "unit_service_area__service_area__name",
        ).order_by(
            "unit_service_area__unit__name",
            "unit_service_area__service_area__name",
        ).annotate(
            Count("unit_service_area__unit__name"),
            Count("unit_service_area__service_area__name"),
        )

    def send_required(self):
        return self.send_empty or self.ses().count() > 0
