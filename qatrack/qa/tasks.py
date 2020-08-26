from django.conf import settings
from django.utils import timezone

from qatrack.qa.models import AutoSave


def clean_autosaves():

    max_date = timezone.now() - timezone.timedelta(days=settings.AUTOSAVE_DAYS_TO_KEEP)
    AutoSave.objects.filter(modified__lte=max_date).delete()
