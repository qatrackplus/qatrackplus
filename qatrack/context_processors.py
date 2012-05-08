from django.conf import settings
from django.contrib.sites.models import Site

from qatrack.qa.models import UnitTestLists, FREQUENCY_CHOICES

def site(request):
    site = Site.objects.get_current()
    return {
        'SITE_NAME': site.name,
        'SITE_URL': site.domain,

        #QA Specific
        'QA_FREQUENCIES' : FREQUENCY_CHOICES,

    }