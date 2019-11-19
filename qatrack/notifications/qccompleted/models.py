from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _l

from qatrack.notifications.common.models import (
    RecipientGroup,
    TestListGroup,
    UnitGroup,
)

tol = settings.TEST_STATUS_DISPLAY.get("tolerance", _l("Tolerance"))
act = settings.TEST_STATUS_DISPLAY.get("action", _l("Action"))


class QCCompletedNotice(models.Model):

    COMPLETED = 0
    TOLERANCE = 10
    ACTION = 20
    FOLLOW_UP = 30

    NOTIFICATION_TYPES = (
        (COMPLETED, _l("Notify when Test List completed")),
        (TOLERANCE, _l("Notify on %s or %s" % (tol, act))),
        (ACTION, _l("Notify on Test at %s level only" % (act))),
        (FOLLOW_UP, _l("Follow up notification")),
    )

    notification_type = models.IntegerField(
        verbose_name=_l("Notification Type"),
        choices=NOTIFICATION_TYPES,
    )

    follow_up_days = models.PositiveIntegerField(
        verbose_name=_l("Follow up days"),
        blank=True,
        null=True,
        help_text=_l(
            "Number of days after TestList completion to send follow up email. Used for follow up notifications only"
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

    class Meta:
        verbose_name = _l("QC Completed Notice")

    def __str__(self):
        return "<QCCompletedNotice(%d, %s)>" % (self.pk, self.get_notification_type_display())
