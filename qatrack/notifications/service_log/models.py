from django.db import models
from django.utils.translation import ugettext_lazy as _l

from qatrack.notifications.common.models import RecipientGroup, UnitGroup


class ServiceEventNotice(models.Model):

    UPDATED = 0

    NOTIFICATION_TYPES = ((UPDATED, _l("Notify when a Service Event is created or modified")),)

    notification_type = models.IntegerField(
        verbose_name=_l("Notification Type"),
        choices=NOTIFICATION_TYPES,
        default=UPDATED,
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

    class Meta:
        verbose_name = _l("Service Event Notice")
