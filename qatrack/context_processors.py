from django.conf import settings
from django.contrib.sites.models import Site
import qatrack.settings
from qatrack.qa.models import (
    UnitTestCollection,
    Frequency,
    TestListInstance,
)

def site(request):
    site = Site.objects.get_current()

    return {
        'SITE_NAME': site.name,
        'SITE_URL': site.domain,
        'VERSION' : qatrack.settings.VERSION,

        #forcing list cuts down number of queries on some pages
        'QA_FREQUENCIES' : list(Frequency.objects.frequency_choices()),
        'UNREVIEWED': TestListInstance.objects.unreviewed().count(),
    }