import json
from django.core.cache import cache
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models import ObjectDoesNotExist
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver

from qatrack.qa.models import Frequency, TestListInstance, UnitTestCollection
from qatrack.units.models import Unit
from qatrack.parts.models import PartUsed, PartStorageCollection
from qatrack.service_log.models import ReturnToServiceQA, ServiceEvent, ServiceEventStatus

cache.delete(settings.CACHE_UNREVIEWED_COUNT)
cache.delete(settings.CACHE_RTS_QA_COUNT)
cache.delete('default-se-status')
cache.delete('se_needing_review_count')


# for u in Unit.objects.filter(active=True):
#     qs = UnitTestCollection.objects.filter(
#         unit=u,
#         active=True
#     ).order_by('name')
#     cache.delete('active_unit_test_collections_for_unit_%s' % u.id)
#     print('%s utc cache deleted' % u.name)

@receiver(pre_delete, sender=PartUsed)
def update_part_storage_quantity(*args, **kwargs):
    pu = kwargs['instance']
    part = pu.part
    storage = pu.from_storage
    quantity = pu.quantity
    # Return parts used to storage:
    if storage:
        try:
            psc = PartStorageCollection.objects.get(part=part, storage=storage)
            psc.quantity += quantity
            psc.save()
        except ObjectDoesNotExist:
            pass


@receiver(post_delete, sender=PartStorageCollection)
def update_part_quantity(*args, **kwargs):

    psc = kwargs['instance']
    part = psc.part
    part.set_quantity_current()


@receiver(post_save, sender=TestListInstance)
@receiver(post_delete, sender=TestListInstance)
def update_unreviewed_cache(*args, **kwargs):
    """When a test list is completed invalidate the unreviewed counts"""
    cache.delete(settings.CACHE_UNREVIEWED_COUNT)
    cache.delete(settings.CACHE_RTS_QA_COUNT)


@receiver(post_save, sender=ReturnToServiceQA)
@receiver(post_delete, sender=ReturnToServiceQA)
def update_unreviewed_cache(*args, **kwargs):
    """When a RTS is completed invalidate the unreviewed counts"""
    cache.delete(settings.CACHE_RTS_QA_COUNT)


@receiver(post_save, sender=ServiceEventStatus)
@receiver(post_delete, sender=ServiceEventStatus)
def update_unreviewed_cache(*args, **kwargs):
    """When a service status is changed invalidate the default and review count"""
    cache.delete('default-se-status')
    cache.delete('se_needing_review_count')


@receiver(post_save, sender=UnitTestCollection)
@receiver(post_delete, sender=UnitTestCollection)
def update_active_unit_test_collections_for_unit(*args, **kwargs):
    unit = kwargs['instance'].unit
    qs = UnitTestCollection.objects.filter(
        unit=unit,
        active=True
    ).order_by('name')
    cache.set('active_unit_test_collections_for_unit_%s' % unit.id, qs)


@receiver(post_save, sender=Unit)
@receiver(post_delete, sender=Unit)
def update_active_unit_test_collections_for_unit(*args, **kwargs):
    unit = kwargs['instance']
    qs = UnitTestCollection.objects.filter(
        unit=unit,
        active=True
    ).order_by('name')
    cache.set('active_unit_test_collections_for_unit_%s' % unit.id, qs)


def site(request):
    cur_site = Site.objects.get_current()

    unreviewed = cache.get(settings.CACHE_UNREVIEWED_COUNT)
    if unreviewed is None:
        unreviewed = TestListInstance.objects.unreviewed_count()
        cache.set(settings.CACHE_UNREVIEWED_COUNT, unreviewed)

    unreviewed_rts = cache.get(settings.CACHE_RTS_QA_COUNT)
    if unreviewed_rts is None:
        unreviewed_rts = ReturnToServiceQA.objects.filter(test_list_instance__isnull=False, test_list_instance__all_reviewed=False).count()
        cache.set(settings.CACHE_RTS_QA_COUNT, unreviewed_rts)

    your_unreviewed = TestListInstance.objects.your_unreviewed_count(request.user)

    default_se_status = cache.get('default-se-status')
    if default_se_status is None:
        default_se_status = ServiceEventStatus.get_default()
        cache.set('default-se-status', default_se_status)

    se_needing_review_count = cache.get('se_needing_review_count')
    if se_needing_review_count is None:
        se_needing_review_count = ServiceEvent.objects.filter(service_status__in=ServiceEventStatus.objects.filter(is_review_required=True), is_review_required=True).count()
        cache.set('se_needing_review_count', se_needing_review_count)

    return {
        'SITE_NAME': cur_site.name,
        'SITE_URL': cur_site.domain,
        'VERSION': settings.VERSION,
        'BUG_REPORT_URL': settings.BUG_REPORT_URL,
        'FEATURE_REQUEST_URL': settings.FEATURE_REQUEST_URL,
        'UNREVIEWED': unreviewed,
        'UNREVIEWED_RTS': unreviewed_rts,
        'YOUR_UNREVIEWED': your_unreviewed,
        'ICON_SETTINGS': settings.ICON_SETTINGS,
        'ICON_SETTINGS_JSON': json.dumps(settings.ICON_SETTINGS),
        'TEST_STATUS_SHORT_JSON': json.dumps(settings.TEST_STATUS_DISPLAY_SHORT),
        'REVIEW_DIFF_COL': settings.REVIEW_DIFF_COL,
        'DEBUG': settings.DEBUG,
        'USE_PARTS': settings.USE_PARTS,
        'DEFAULT_SE_STATUS': default_se_status,
        'SE_NEEDING_REVIEW_COUNT': se_needing_review_count,
    }
