from datetime import time as dt_time

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l
from recurrence.fields import RecurrenceField

from qatrack.notifications.common.models import (
    RecipientGroup,
    TestListGroup,
    UnitGroup,
)
from qatrack.qa.models import UnitTestCollection
from qatrack.qatrack_core.utils import today_start_end


class QCSchedulingNotice(models.Model):

    ALL = 0
    DUE = 10
    UPCOMING_AND_DUE = 20
    UPCOMING = 30

    NOTIFICATION_TYPES = (
        (ALL, _l("Notify About All Test Lists Due Dates")),
        (DUE, _l("Notify About Test Lists Currently Due & Overdue")),
        (UPCOMING_AND_DUE, _l("Notify About Test Lists Currently Due & Overdue, and Upcoming Due Dates")),
        (UPCOMING, _l("Notify About Test Lists Upcoming Due Dates Only")),
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

    test_lists = models.ForeignKey(
        TestListGroup,
        verbose_name=_l("Test List Group filter"),
        help_text=_l(
            "Select which group of Test Lists this notification should be limited to. "
            "Leave blank to include all Test Lists."
        ),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    last_sent = models.DateTimeField(null=True, editable=False)

    class Meta:
        verbose_name = _l("QC Scheduling Notice")

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

    def utcs(self):
        """Return UTCS relevant to this notice"""

        utcs = UnitTestCollection.objects.filter(active=True, unit__active=True)

        if self.units_id:
            utcs = utcs.filter(unit__in=self.units.units.all())

        if self.test_lists_id:
            all_tls = self.test_lists.test_lists.all()
            utcs = utcs.filter(Q(test_list__in=all_tls) | Q(test_list_cycle__test_lists__in=all_tls))

        return utcs.order_by("unit__%s" % settings.ORDER_UNITS_BY, "due_date")

    def all(self):
        return self.utcs().exclude(due_date=None)

    def upcoming(self, include_overdue=False):
        """Return UTCS that will be coming due in the future. Optionally
        include test lists that are currently due and overdue"""

        start, end = today_start_end()
        end = end + timezone.timedelta(days=self.future_days)

        utcs = self.utcs().filter(due_date__lte=end)
        if not include_overdue:
            utcs = utcs.filter(due_date__gte=start)

        return utcs

    def due_and_overdue(self):
        """Return UTCS that are currently due or overdue"""
        start, end = today_start_end()
        return self.utcs().filter(due_date__lte=end)

    def upcoming_and_due(self):
        """Return UTCS that are either coming due soon or currently due or overdue"""
        return self.upcoming(include_overdue=True)

    def utcs_to_notify(self):
        dispatch = {
            self.ALL: self.all,
            self.DUE: self.due_and_overdue,
            self.UPCOMING_AND_DUE: self.upcoming_and_due,
            self.UPCOMING: self.upcoming,
        }
        return dispatch[self.notification_type]()

    def send_required(self):
        return self.send_empty or self.utcs_to_notify().count() > 0
