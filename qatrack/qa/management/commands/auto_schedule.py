from django.core.management.base import BaseCommand, CommandError
from qatrack.qa.models import UnitTestCollection

#============================================================================


class Command(BaseCommand):
    """A management command to set due_date (based on assigned frequency)
    for all UnitTestCollections that have auto_schedule = True.
    """

    help = 'commands to enable/disable auto scheduling and set due dates'

    #----------------------------------------------------------------------
    def handle(self, *args, **kwargs):
        handlers = {
            "enable-all": self.enable_all,
            "disable-all": self.disable_all,
            "schedule-all": self.schedule_all,
            "unschedule-all": self.unschedule_all,
        }

        if not args or args[0] not in handlers.keys():
            valid = ', '.join(["'%s'" % x for x in handlers.keys()])
            raise CommandError("Valid arguments are %s" % (valid))

        handlers[args[0]]()

    #----------------------------------------------------------------------
    def enable_all(self):
        """Sets auto_schedule = True on all UnitTestCollections with assigned frequencies"""
        UnitTestCollection.objects.exclude(frequency=None).update(auto_schedule=True)
        self.stdout.write("Successfully enabled auto scheduling for all test lists")

    #----------------------------------------------------------------------
    def disable_all(self):
        """Sets auto_schedule = False on all UnitTestCollections"""
        UnitTestCollection.objects.update(auto_schedule=False)
        self.stdout.write("Successfully disabled auto scheduling for all test lists")

    #----------------------------------------------------------------------
    def schedule_all(self):
        """Sets due date for all UnitTestCollections with assigned frequencies"""
        utcs = UnitTestCollection.objects.exclude(frequency=None)
        for utc in utcs:
            utc.set_due_date()

        self.stdout.write("Successfully set all due dates")

    #----------------------------------------------------------------------
    def unschedule_all(self):
        """Sets due_date=None on all UnitTestCollections"""
        UnitTestCollection.objects.update(due_date=None)
        self.stdout.write("Successfully un-set all due dates")
