from django.core.cache import cache
from django.conf import settings
from django.contrib.sites.models import Site
from qatrack.qa.models import Frequency, TestListInstance


def site(request):
    site = Site.objects.get_current()

    unreviewed = cache.get(settings.CACHE_UNREVIEWED_COUNT)
    if unreviewed is None:
        unreviewed = TestListInstance.objects.unreviewed_count()
        cache.set(settings.CACHE_UNREVIEWED_COUNT, unreviewed)

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

        # forcing list cuts down number of queries on some pages
        'QA_FREQUENCIES': qa_frequencies,
        'UNREVIEWED': unreviewed,
    }
