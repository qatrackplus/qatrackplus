from django.db import models
from django.utils.translation import gettext_lazy as _l

from qatrack.notifications.common.models import RecipientGroup, UnitGroup


class FaultNotice(models.Model):

    LOGGED = 0

    NOTIFICATION_TYPES = (
        (LOGGED, _l("Notify when fault logged")),
    )

    notification_type = models.IntegerField(
        verbose_name=_l("Notification Type"),
        choices=NOTIFICATION_TYPES,
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
        verbose_name = _l("Fault Logged Notice")

    def __str__(self):
        return "<FaultNotice(%d, %s)>" % (self.pk, self.get_notification_type_display())
