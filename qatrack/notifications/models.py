from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.translation import ugettext_lazy as _l

from qatrack.units.models import Unit

# this import has to be here so that the signal handlers get registered
from . import handlers  # NOQA

TOLERANCE = 10
ACTION = 20

tol = settings.TEST_STATUS_DISPLAY.get("tolerance", "Tolerance")
act = settings.TEST_STATUS_DISPLAY.get("action", "Action")

WARNING_LEVELS = (
    (TOLERANCE, "Notify on %s or %s" % (tol, act)),
    (ACTION, "Notify on Test at %s level only" % (act)),
)


class NotificationSubscription(models.Model):

    warning_level = models.IntegerField(choices=WARNING_LEVELS)

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
            "Select which Units notifications should be sent to this group for. Leave blank to include all units"
        ),
        blank=True,
    )

    def __str__(self):
        return "<NotificationSubscription(%s)>" % self.id
