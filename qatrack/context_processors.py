import json
from random import Random

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.db.models import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from django.utils.formats import get_format

from qatrack.faults.models import Fault
from qatrack.parts.models import PartStorageCollection, PartUsed
from qatrack.qa.models import TestListInstance, UnitTestCollection
from qatrack.service_log.models import (
    ReturnToServiceQA,
    ServiceEvent,
    ServiceEventStatus,
)
from qatrack.units.models import Unit

cache.delete(settings.CACHE_UNREVIEWED_FAULT_COUNT)
cache.delete(settings.CACHE_UNREVIEWED_COUNT)
cache.delete(settings.CACHE_UNREVIEWED_COUNT_USER)
cache.delete(settings.CACHE_RTS_QA_COUNT)
cache.delete(settings.CACHE_RTS_INCOMPLETE_QA_COUNT)
cache.delete(settings.CACHE_DEFAULT_SE_STATUS)
cache.delete(settings.CACHE_SE_NEEDING_REVIEW_COUNT)
cache.delete(settings.CACHE_IN_PROGRESS_COUNT_USER)
cache.delete(settings.CACHE_SERVICE_STATUS_COLOURS)
cache.delete(settings.CACHE_SL_NOTIFICATION_TOTAL)


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
@receiver(post_save, sender=User)
@receiver(post_save, sender=Group)
def update_unreviewed_cache(*args, **kwargs):
    """When a test list is completed invalidate the unreviewed counts"""
    cache.delete(settings.CACHE_UNREVIEWED_COUNT)
    cache.delete(settings.CACHE_UNREVIEWED_COUNT_USER)
    cache.delete(settings.CACHE_RTS_QA_COUNT)
    cache.delete(settings.CACHE_RTS_INCOMPLETE_QA_COUNT)
    cache.delete(settings.CACHE_IN_PROGRESS_COUNT_USER)
    cache.delete(settings.CACHE_SL_NOTIFICATION_TOTAL)


@receiver(post_save, sender=ReturnToServiceQA)
@receiver(post_delete, sender=ReturnToServiceQA)
def update_rts_cache(*args, **kwargs):
    """When a RTS is completed invalidate the unreviewed counts"""
    cache.delete(settings.CACHE_RTS_QA_COUNT)
    cache.delete(settings.CACHE_RTS_INCOMPLETE_QA_COUNT)
    cache.delete(settings.CACHE_SL_NOTIFICATION_TOTAL)


@receiver(post_save, sender=ServiceEventStatus)
@receiver(post_delete, sender=ServiceEventStatus)
@receiver(post_delete, sender=ServiceEvent)
def update_se_cache(*args, **kwargs):
    """When a service status is changed invalidate the default and review count"""
    cache.delete(settings.CACHE_DEFAULT_SE_STATUS)
    cache.delete(settings.CACHE_SE_NEEDING_REVIEW_COUNT)
    cache.delete(settings.CACHE_SL_NOTIFICATION_TOTAL)


@receiver(post_save, sender=Fault)
@receiver(post_delete, sender=Fault)
def update_faults_cache(*args, **kwargs):
    """When a fault is changed invalidate the default and review count"""
    cache.delete(settings.CACHE_UNREVIEWED_FAULT_COUNT)


@receiver(post_save, sender=UnitTestCollection)
@receiver(post_delete, sender=UnitTestCollection)
def update_active_unit_test_collections_for_unit_utc(*args, **kwargs):
    unit = kwargs['instance'].unit
    qs = UnitTestCollection.objects.filter(
        unit=unit,
        active=True
    ).order_by('name')
    cache.set(settings.CACHE_ACTIVE_UTCS_FOR_UNIT_.format(unit.id), qs)


@receiver(post_save, sender=Unit)
@receiver(post_delete, sender=Unit)
def update_active_unit_test_collections_for_unit(*args, **kwargs):
    unit = kwargs['instance']
    qs = UnitTestCollection.objects.filter(
        unit=unit,
        active=True
    ).order_by('name')
    cache.set(settings.CACHE_ACTIVE_UTCS_FOR_UNIT_.format(unit.id), qs)


@receiver(post_save, sender=ServiceEventStatus)
@receiver(post_delete, sender=ServiceEventStatus)
def update_colours(*args, **kwargs):
    service_status_colours = {ses.name: ses.colour for ses in ServiceEventStatus.objects.all()}
    cache.set(settings.CACHE_SERVICE_STATUS_COLOURS, service_status_colours)


def site(request):

    context = {
        'SELF_REGISTER': settings.ACCOUNTS_SELF_REGISTER,
        'USE_ADFS': settings.USE_ADFS,
        'ACCOUNTS_PASSWORD_RESET': settings.ACCOUNTS_PASSWORD_RESET,
        'VERSION': settings.VERSION,
        'CSS_VERSION': Random().randint(1, 1000) if settings.DEBUG else settings.VERSION,
        'BUG_REPORT_URL': settings.BUG_REPORT_URL,
        'FEATURE_REQUEST_URL': settings.FEATURE_REQUEST_URL,
        'ICON_SETTINGS': settings.ICON_SETTINGS,
        'ICON_SETTINGS_JSON': json.dumps(settings.ICON_SETTINGS),
        'TEST_STATUS_SHORT_JSON': json.dumps(settings.TEST_STATUS_DISPLAY_SHORT),
        'REVIEW_DIFF_COL': settings.REVIEW_DIFF_COL,
        'DEBUG': settings.DEBUG,
        'USE_SQL_REPORTS': settings.USE_SQL_REPORTS,
        'USE_ISSUES': settings.USE_ISSUES,

        # JavaScript Date Formats
        'MOMENT_DATE_DATA_FMT': get_format("MOMENT_DATE_DATA_FMT"),
        'MOMENT_DATE_FMT': get_format("MOMENT_DATE_FMT"),
        'MOMENT_DATETIME_FMT': get_format("MOMENT_DATETIME_FMT"),
        'FLATPICKR_DATE_FMT': get_format("FLATPICKR_DATE_FMT"),
        'FLATPICKR_DATETIME_FMT': get_format("FLATPICKR_DATETIME_FMT"),
        'DATERANGEPICKER_DATE_FMT': get_format("DATERANGEPICKER_DATE_FMT"),
    }
    cur_site = get_current_site(request)
    context.update({'SITE_NAME': cur_site.name, 'SITE_URL': cur_site.domain})

    context['UNREVIEWED'] = cache.get_or_set(
        settings.CACHE_UNREVIEWED_COUNT,
        TestListInstance.objects.unreviewed_count,
    )

    context['USERS_UNREVIEWED'] = get_user_count(
        request,
        settings.CACHE_UNREVIEWED_COUNT_USER,
        TestListInstance.objects.your_unreviewed_count,
    )

    context['DEFAULT_SE_STATUS'] = cache.get_or_set(
        settings.CACHE_DEFAULT_SE_STATUS,
        ServiceEventStatus.get_default,
    )

    context['SE_NEEDING_REVIEW_COUNT'] = cache.get_or_set(
        settings.CACHE_SE_NEEDING_REVIEW_COUNT,
        ServiceEvent.objects.review_required_count,
    )

    context['SE_RTS_INCOMPLETE_QA_COUNT'] = cache.get_or_set(
        settings.CACHE_RTS_INCOMPLETE_QA_COUNT,
        ReturnToServiceQA.objects.incomplete_count,
    )

    context['SE_RTS_UNREVIEWED_QA_COUNT'] = cache.get_or_set(
        settings.CACHE_RTS_QA_COUNT,
        ReturnToServiceQA.objects.unreviewed_count,
    )

    context['SL_NOTIFICATION_TOTAL'] = cache.get_or_set(
        settings.CACHE_SL_NOTIFICATION_TOTAL,
        lambda: (
            get_sl_notification_total(
                request,
                context['SE_NEEDING_REVIEW_COUNT'],
                context['SE_RTS_INCOMPLETE_QA_COUNT'],
                context['SE_RTS_UNREVIEWED_QA_COUNT'],
            )
        ),
    )

    context['FAULTS_UNREVIEWED'] = cache.get_or_set(
        settings.CACHE_UNREVIEWED_FAULT_COUNT,
        Fault.objects.unreviewed_count,
    )

    context['USERS_IN_PROGRESS'] = get_user_count(
        request,
        settings.CACHE_IN_PROGRESS_COUNT_USER,
        TestListInstance.objects.your_in_progress_count,
    )

    cache.get_or_set(
        settings.CACHE_SERVICE_STATUS_COLOURS,
        lambda: {ses.name: ses.colour for ses in ServiceEventStatus.objects.all()}
    )

    return context


def get_user_count(request, key, manager_method):

    counts = cache.get(key)
    if counts is None and hasattr(request, "user"):
        user_count = manager_method(request.user)
        counts = {request.user.pk: user_count}
        cache.set(key, counts)
    else:
        try:
            user_count = counts[request.user.pk]
        except KeyError:
            user_count = manager_method(request.user)
            counts[request.user.pk] = user_count
            cache.set(key, counts)
        except Exception:
            user_count = 0

    return user_count


def get_sl_notification_total(request, se_unreviewed, rts_incomplete, rts_unreviewed):
    perms = [
        ('service_log.review_serviceevent', se_unreviewed),
        ('service_log.perform_returntoserviceqa', rts_incomplete),
        ('qa.can_review', rts_unreviewed),
    ]
    return sum(count for perm, count in perms if hasattr(request, 'user') and request.user.has_perm(perm))
