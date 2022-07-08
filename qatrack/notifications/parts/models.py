from django.db import models
from django.utils.translation import gettext_lazy as _l

from qatrack.notifications.common.models import RecipientGroup
from qatrack.parts.models import PartCategory


class PartCategoryGroup(models.Model):

    name = models.CharField(max_length=255, help_text=_l("Enter a name for this group of part categories"))

    part_categories = models.ManyToManyField(
        PartCategory,
        help_text=_l("Select which Part Categories should be included in this notification group."),
    )

    def __str__(self):
        return self.name


class PartNotice(models.Model):

    LOW_INVENTORY = 'low_inventory'

    NOTIFICATION_TYPES = ((
        LOW_INVENTORY, _l("Notify when inventory for a part falls below it's Low Inventory threshold")
    ),)

    notification_type = models.CharField(
        verbose_name=_l("Notification Type"),
        choices=NOTIFICATION_TYPES,
        default=LOW_INVENTORY,
        blank=False,
        max_length=128,
    )

    recipients = models.ForeignKey(
        RecipientGroup,
        verbose_name=_l("Recipients"),
        help_text=_l("Choose the group of recipients who should receive these notifications"),
        on_delete=models.PROTECT,
    )

    part_categories = models.ForeignKey(
        PartCategoryGroup,
        verbose_name=_l("Part Group filter"),
        help_text=_l(
            "Select which group of parts this notification should be limited to. Leave blank to include all parts"
        ),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    class Meta:
        verbose_name = _l("Part Notice")
