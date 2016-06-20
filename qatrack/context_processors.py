import json
from django.core.cache import cache
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from qatrack.qa.models import Frequency, TestListInstance

cache.delete(settings.CACHE_UNREVIEWED_COUNT)
cache.delete(settings.CACHE_QA_FREQUENCIES)


@receiver(post_save, sender=TestListInstance)
@receiver(post_delete, sender=TestListInstance)
def update_unreviewed_cache(*args, **kwargs):
    """When a test list is completed invalidate the unreviewed counts"""
    cache.delete(settings.CACHE_UNREVIEWED_COUNT)


@receiver(post_save, sender=Frequency)
@receiver(post_delete, sender=Frequency)
def update_qa_freq_cache(*args, **kwargs):
    """When a frequency is changed invalidate the frequencies"""
    cache.delete(settings.CACHE_QA_FREQUENCIES)


def site(request):
    site = Site.objects.get_current()

    unreviewed = cache.get(settings.CACHE_UNREVIEWED_COUNT)
    if unreviewed is None:
        unreviewed = TestListInstance.objects.unreviewed_count()
        cache.set(settings.CACHE_UNREVIEWED_COUNT, unreviewed)

    your_unreviewed = TestListInstance.objects.your_unreviewed_count(request.user)

    qa_frequencies = cache.get(settings.CACHE_QA_FREQUENCIES)
    if qa_frequencies is None:
        qa_frequencies = list(Frequency.objects.frequency_choices())
        cache.set(settings.CACHE_QA_FREQUENCIES, qa_frequencies)

    return {
        'SITE_NAME': site.name,
        'SITE_URL': site.domain,
        'VERSION': settings.VERSION,
        'BUG_REPORT_URL': settings.BUG_REPORT_URL,
        'FEATURE_REQUEST_URL': settings.FEATURE_REQUEST_URL,
        'QA_FREQUENCIES': qa_frequencies,
        'UNREVIEWED': unreviewed,
        'YOUR_UNREVIEWED': your_unreviewed,
        'ICON_SETTINGS': settings.ICON_SETTINGS,
        'ICON_SETTINGS_JSON': json.dumps(settings.ICON_SETTINGS),
        'TEST_STATUS_SHORT_JSON': json.dumps(settings.TEST_STATUS_DISPLAY_SHORT),
        'REVIEW_DIFF_COL': settings.REVIEW_DIFF_COL,
    }
