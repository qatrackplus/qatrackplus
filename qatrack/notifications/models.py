from django.conf import settings
from django.db import models
from django.contrib.auth.models import Group

# this import has to be here so that the signal handlers get registered
import handlers  # NOQA


TOLERANCE = 10
ACTION = 20

tol = settings.TEST_STATUS_DISPLAY.get("tolerance", "Tolerance")
act = settings.TEST_STATUS_DISPLAY.get("action", "Action")

WARNING_LEVELS = (
    (TOLERANCE, "Notify on %s or %s" % (tol, act)),
    (ACTION, "Notify on Test at %s level only" % (act)),
)

#============================================================================


class NotificationSubscription(models.Model):

    group = models.ForeignKey(Group, unique=True)

    warning_level = models.IntegerField(choices=WARNING_LEVELS)

    #----------------------------------------------------------------------
    def __unicode__(self):
        return "<NotificationSubscription(%s)>" % self.group.name
