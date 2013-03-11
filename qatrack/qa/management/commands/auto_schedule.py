from django.core.management.base import BaseCommand, CommandError
from qatrack.qa.models import UnitTestCollection

#============================================================================
class Command(BaseCommand):
    """A management command to set due_date (based on assigned frequency)
    for all UnitTestCollections that have auto_schedule = True.
    """

    #----------------------------------------------------------------------
    def handle(self,*args,**kwargs):
        utcs = UnitTestCollection.objects.filter(auto_schedule=True).exclude(frequency=None)

        for utc in utcs:
            utc.set_due_date()

