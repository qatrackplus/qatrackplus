from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from qatrack.qa.signals import loaded_from_fixture
from qatrack.service_log import models


def update_last_instances(service_event):
    schedule = service_event.service_event_schedule
    if not schedule:
        return

    try:
        last_instance = models.ServiceEvent.objects.filter(service_event_schedule=schedule).latest("datetime_service")
    except models.ServiceEvent.DoesNotExist:
        last_instance = None
    except models.ServiceEventSchedule.DoesNotExist:
        # this will occur when a ServiceEventSchedule deletion cascades and
        # deletes all service_events_associated with it.
        # in that case it doesn't make sense to try to update anything
        return

    schedule.last_instance = last_instance
    due_date = schedule.calc_due_date()

    # use update so not to trigger post save signal
    models.ServiceEventSchedule.objects.filter(pk=schedule.pk).update(
        due_date=due_date,
        last_instance=last_instance,
    )


@receiver(post_save, sender=models.ServiceEvent)
def on_service_event_saved(*args, **kwargs):

    if not loaded_from_fixture(kwargs):
        update_last_instances(kwargs["instance"])


@receiver(post_delete, sender=models.ServiceEvent)
def on_service_event_deleted(*args, **kwargs):
    """update last_instance if available"""
    update_last_instances(kwargs["instance"])


@receiver(post_save, sender=models.ReturnToServiceQA, dispatch_uid="sl_update_rts_cache_post_save")
@receiver(post_delete, sender=models.ReturnToServiceQA, dispatch_uid="sl_update_rts_cache_post_delete")
def update_rts_cache(sender, **kwargs):
    """When a RTS is completed invalidate the unreviewed counts"""
    cache.delete(settings.CACHE_RTS_QA_COUNT)
    cache.delete(settings.CACHE_RTS_INCOMPLETE_QA_COUNT)
    cache.delete(settings.CACHE_SL_NOTIFICATION_TOTAL)


@receiver(post_save, sender=models.ServiceEventStatus, dispatch_uid="sl_update_se_cache_ses_post_save")
@receiver(post_delete, sender=models.ServiceEventStatus, dispatch_uid="sl_update_se_cache_ses_post_delete")
@receiver(post_delete, sender=models.ServiceEvent, dispatch_uid="sl_update_se_cache_se_post_delete")
@receiver(post_save, sender=models.ServiceEvent, dispatch_uid="sl_update_se_cache_se_post_save")
def update_se_cache(sender, **kwargs):
    """When a service status is changed invalidate the default and review count"""
    if sender == models.ServiceEventStatus:
        cache.delete(settings.CACHE_DEFAULT_SE_STATUS)
    cache.delete(settings.CACHE_SE_NEEDING_REVIEW_COUNT)
    cache.delete(settings.CACHE_SL_NOTIFICATION_TOTAL)


@receiver(post_save, sender=models.ServiceEventStatus, dispatch_uid="sl_update_colours_post_save")
@receiver(post_delete, sender=models.ServiceEventStatus, dispatch_uid="sl_update_colours_post_delete")
def update_colours(sender, **kwargs):
    service_status_colours = {ses.name: ses.colour for ses in models.ServiceEventStatus.objects.all()}
    cache.set(settings.CACHE_SERVICE_STATUS_COLOURS, service_status_colours)
