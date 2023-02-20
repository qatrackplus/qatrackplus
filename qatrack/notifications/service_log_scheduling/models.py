from datetime import time as dt_time

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l
from recurrence.fields import RecurrenceField

from qatrack.notifications.common.models import RecipientGroup, UnitGroup
from qatrack.qatrack_core.scheduling import RecurrenceFieldMixin
from qatrack.qatrack_core.utils import today_start_end
from qatrack.service_log.models import ServiceEventSchedule


class ServiceEventSchedulingNotice(RecurrenceFieldMixin, models.Model):

    ALL = 0
    DUE = 10
    UPCOMING_AND_DUE = 20
    UPCOMING = 30

    NOTIFICATION_TYPES = (
        (ALL, _l("Notify About All Service Event Schedule Due Dates")),
        (DUE, _l("Notify About Scheduled Service Events Currently Due & Overdue")),
        (UPCOMING_AND_DUE, _l("Notify About Scheduled Service Events Currently Due & Overdue, and Upcoming Due Dates")),
        (UPCOMING, _l("Notify About Scheduled Service Events Upcoming Due Dates Only")),
    )

    TIME_CHOICES = [(dt_time(x // 60, x % 60), "%02d:%02d" % (x // 60, x % 60)) for x in range(0, 24 * 60, 15)]

    notification_type = models.IntegerField(
        verbose_name=_l("Notification Type"),
        choices=NOTIFICATION_TYPES,
    )

    send_empty = models.BooleanField(
        verbose_name=_l("Send Empty Notices"),
        help_text=_l("Check to send notices even if there's no QC to currently notify about"),
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

    future_days = models.PositiveIntegerField(
        verbose_name=_l("Future Days"),
        blank=True,
        null=True,
        help_text=_l(
            "How many days in the future should notices about upcoming QC due dates include. "
            "A value of zero will only include test lists due today."
        ),
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
        verbose_name = _l("Service Event Scheduling Notice")

    @property
    def is_all(self):
        return self.notification_type == self.ALL

    @property
    def is_due(self):
        return self.notification_type == self.DUE

    @property
    def is_upcoming_and_due(self):
        return self.notification_type == self.UPCOMING_AND_DUE

    @property
    def is_upcoming(self):
        return self.notification_type == self.UPCOMING

    def schedules(self):
        """Return ServiceEventSchedule relevant to this notice"""

        schedules = ServiceEventSchedule.objects.filter(active=True)

        if self.units_id:
            schedules = schedules.filter(unit_service_area__unit__in=self.units.units.all())

        return schedules.order_by(
            "unit_service_area__unit__%s" % settings.ORDER_UNITS_BY,
            "unit_service_area__service_area__name",
            "due_date",
        )

    def all(self):
        return self.schedules().exclude(due_date=None)

    def upcoming(self, include_overdue=False):
        """Return Schedules that will be coming due in the future. Optionally
        include test lists that are currently due and overdue"""

        start, end = today_start_end()
        end = end + timezone.timedelta(days=self.future_days)

        schedules = self.schedules().filter(due_date__lte=end)
        if not include_overdue:
            schedules = schedules.filter(due_date__gte=start)

        return schedules

    def due_and_overdue(self):
        """Return Schedules that are currently due or overdue"""
        start, end = today_start_end()
        return self.schedules().filter(due_date__lte=end)

    def upcoming_and_due(self):
        """Return Schedules that are either coming due soon or currently due or overdue"""
        return self.upcoming(include_overdue=True)

    def schedules_to_notify(self):
        dispatch = {
            self.ALL: self.all,
            self.DUE: self.due_and_overdue,
            self.UPCOMING_AND_DUE: self.upcoming_and_due,
            self.UPCOMING: self.upcoming,
        }
        return dispatch[self.notification_type]()

    def send_required(self):
        return self.send_empty or self.schedules_to_notify().count() > 0
