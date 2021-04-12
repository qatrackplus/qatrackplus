from django.db import models
from django.utils.translation import gettext_lazy as _l

from qatrack.notifications.common.models import RecipientGroup, UnitGroup


class ServiceEventNotice(models.Model):

    UPDATED_OR_CREATED = 'new_se_mod_se'
    NEW_SERVICE_EVENT = 'new_se'
    MODIFIED_SERVICE_EVENT = 'mod_se'
    STATUS_SERVICE_EVENT = 'stat_se'
    CHANGED_RTSQA = 'rtsqa'
    PERFORMED_RTS = 'perf_rts'
    APPROVED_RTS = 'app_rts'
    DELETED_SERVICE_EVENT = 'del_se'

    NOTIFICATION_TYPES = (
        (UPDATED_OR_CREATED, _l("Notify when a Service Event is created or modified in any way")),
        (NEW_SERVICE_EVENT, _l("Notify when a Service Event is created")),
        (MODIFIED_SERVICE_EVENT, _l("Notify when a Service Event is modified in any way")),
        (STATUS_SERVICE_EVENT, _l("Notify when a Service Event Status is changed")),
        (CHANGED_RTSQA, _l("Notify when Return To Service QC is changed")),
        (PERFORMED_RTS, _l("Notify when Return To Service QC is performed")),
        (APPROVED_RTS, _l("Notify when Return To Service QC is approved")),
    )

    notification_type = models.CharField(
        verbose_name=_l("Notification Type"),
        choices=NOTIFICATION_TYPES,
        default=UPDATED_OR_CREATED,
        blank=False,
        max_length=128,
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
