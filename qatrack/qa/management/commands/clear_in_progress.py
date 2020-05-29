from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from qatrack.qa.models import TestListInstance


class Command(BaseCommand):
    """A management command to delete all in progress test lists"""

    help = 'command to delete all in progress test lists'

    def handle(self, *args, **kwargs):

        objs = TestListInstance.objects.in_progress()
        counts = objs.count()

        if counts <= 0:
            print("Nothing to delete")
            return
        prompt = (
            "Are you sure you want to delete %d in progress test lists (they can not be restored) (y/N): " % counts
        )
        confirm = input(prompt)
        if confirm.lower() != 'y':
            print("Action cancelled")
            return

        objs.delete()
        cache.delete(settings.CACHE_IN_PROGRESS_COUNT_USER)
        print("Deleted %d In Progress TestListInstances" % counts)
