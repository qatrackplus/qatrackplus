import json
import os
from random import Random

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.utils.formats import get_format
from django.utils.translation import get_language_info

from qatrack.faults.models import Fault
from qatrack.qa.models import TestListInstance
from qatrack.service_log.models import (
    ReturnToServiceQA,
    ServiceEvent,
    ServiceEventStatus,
)

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
        'CSRF_COOKIE_NAME': settings.CSRF_COOKIE_NAME,
        'USE_SQL_REPORTS': settings.USE_SQL_REPORTS,
        'USE_ISSUES': settings.USE_ISSUES,
        'PING_INTERVAL_S': settings.PING_INTERVAL_S,

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


def available_languages(request):
    """
    Context processor to provide available languages for the language switcher dropdown.
    LANGUAGES setting takes precedence over auto-detection when explicitly set.
    """
    languages = []
    
    # Check if LANGUAGES is explicitly set in settings
    languages_explicitly_set = hasattr(settings, 'LANGUAGES') and settings.LANGUAGES
    
    # Get languages from Django settings
    if languages_explicitly_set:
        for lang_code, lang_name in settings.LANGUAGES:
            try:
                # Get detailed language info
                lang_info = get_language_info(lang_code)
                languages.append({
                    'code': lang_code,
                    'name': lang_info['name_local'],  # Name in the language itself
                    'name_translated': lang_name,     # Name in current language
                    'bidi': lang_info['bidi'],       # Right-to-left support
                })
            except Exception:
                # Fallback if language info not available
                languages.append({
                    'code': lang_code,
                    'name': lang_name,
                    'name_translated': lang_name,
                    'bidi': False,
                })
    
    # Only scan locale directory if LANGUAGES is NOT explicitly set
    # This allows auto-detection when no LANGUAGES is specified
    if not languages_explicitly_set and hasattr(settings, 'LOCALE_PATHS'):
        for locale_path in settings.LOCALE_PATHS:
            if os.path.exists(locale_path):
                try:
                    for item in os.listdir(locale_path):
                        item_path = os.path.join(locale_path, item)
                        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, 'LC_MESSAGES')):
                            # This looks like a valid locale directory
                            if not any(lang['code'] == item for lang in languages):
                                try:
                                    lang_info = get_language_info(item)
                                    languages.append({
                                        'code': item,
                                        'name': lang_info['name_local'],
                                        'name_translated': lang_info['name'],
                                        'bidi': lang_info['bidi'],
                                    })
                                except Exception:
                                    # Fallback for unknown languages
                                    languages.append({
                                        'code': item,
                                        'name': item.upper(),
                                        'name_translated': item.upper(),
                                        'bidi': False,
                                    })
                except (OSError, PermissionError):
                    # Skip if we can't read the directory
                    pass
    
    # Sort languages by code for consistent ordering
    languages.sort(key=lambda x: x['code'])
    
    return {'available_languages': languages}
