from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.translation import ugettext_lazy as _l

from qatrack.qa.models import TestList
from qatrack.units.models import Unit

# this import has to be here so that the signal handlers get registered
from . import handlers  # NOQA

COMPLETED = 0
TOLERANCE = 10
ACTION = 20
FOLLOW_UP = 30

tol = settings.TEST_STATUS_DISPLAY.get("tolerance", _l("Tolerance"))
act = settings.TEST_STATUS_DISPLAY.get("action", _l("Action"))

NOTIFICATION_TYPES = (
    (COMPLETED, _l("Notify when Test List completed")),
    (TOLERANCE, _l("Notify on %s or %s" % (tol, act))),
    (ACTION, _l("Notify on Test at %s level only" % (act))),
    (FOLLOW_UP, _l("Follow up notification")),
)


class NotificationSubscription(models.Model):

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

    groups = models.ManyToManyField(
        Group,
        help_text=_l("Select which groups this notification should be sent to."),
        blank=True,
        related_name="notificationsubscriptions",
    )

    users = models.ManyToManyField(
        User,
        help_text=_l("Select individual users to include in these notifications"),
        blank=True,
        related_name="notificationsubscriptions",
    )

    units = models.ManyToManyField(
        Unit,
        help_text=_l(
            "Select which Units should be included in this notification. Leave blank to include all units"
        ),
        blank=True,
    )

    test_lists = models.ManyToManyField(
        TestList,
        help_text=_l(
            "Select which Test Lists should be included in this notification. Leave blank to include all Test Lists"
        ),
        blank=True,
    )

    def __str__(self):
        return "<NotificationSubscription(%d, %s)>" % (self.pk, self.get_notification_type_display())
