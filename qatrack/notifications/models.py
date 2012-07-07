from django.db import models
from django.contrib.auth.models import Group, User
from django.utils.translation import ugettext as _

# this import has to be here so that the signal handlers get registered
import handlers


#----------------------------------------------------------------------
def users_subscribed_to_failures():
    return User.objects.filter(
        groups__notificationsubscription_set__notify_on_failure=True
    ).distinct()


TOLERANCE = 10
ACTION = 20

WARNING_LEVELS = (
    (TOLERANCE,"Notify on Tolerance or Action"),
    (ACTION,"Notify on Test at Action level only"),
)

#============================================================================
class NotificationSubscription(models.Model):

    group = models.ForeignKey(Group,unique=True)

    warning_level = models.IntegerField(choices=WARNING_LEVELS)

    #----------------------------------------------------------------------
    def __unicode__(self):
        return "<NotificationSubscription(%s)>"%self.group.name

