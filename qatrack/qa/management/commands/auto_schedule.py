from django.core.management.base import BaseCommand

from qatrack.qa.models import UnitTestCollection


class Command(BaseCommand):
    """A management command to set due_date (based on assigned frequency)
    for all UnitTestCollections that have auto_schedule = True.
    """

    help = 'commands to enable/disable auto scheduling and set due dates'

    # The action name a user types, mapped to the method that performs it.
    #
    # One mapping, used for both the parser's `choices` and the dispatch below,
    # so the set of actions the command advertises cannot drift from the set it
    # can actually run. `docs/admin/qa/auto_schedule.rst` documents these four.
    ACTIONS = {
        "enable-all": "enable_all",
        "disable-all": "disable_all",
        "schedule-all": "schedule_all",
        "unschedule-all": "unschedule_all",
    }

    def add_arguments(self, parser):
        # Without this the command had no positional argument at all, so argparse
        # rejected every documented action with "unrecognized arguments", while
        # running it bare printed the four names it would not accept.
        parser.add_argument(
            'action',
            choices=sorted(self.ACTIONS),
            help='the scheduling action to perform',
        )

    def handle(self, *args, **options):
        getattr(self, self.ACTIONS[options['action']])()

    def enable_all(self):
        """Sets auto_schedule = True on all UnitTestCollections with assigned frequencies"""
        UnitTestCollection.objects.exclude(frequency=None).update(auto_schedule=True)
        self.stdout.write("Successfully enabled auto scheduling for all test lists")

    def disable_all(self):
        """Sets auto_schedule = False on all UnitTestCollections"""
        UnitTestCollection.objects.update(auto_schedule=False)
        self.stdout.write("Successfully disabled auto scheduling for all test lists")

    def schedule_all(self):
        """Sets due date for all UnitTestCollections with assigned frequencies"""
        utcs = UnitTestCollection.objects.exclude(frequency=None)
        for utc in utcs:
            utc.set_due_date()

        self.stdout.write("Successfully set all due dates")

    def unschedule_all(self):
        """Sets due_date=None on all UnitTestCollections"""
        UnitTestCollection.objects.update(due_date=None)
        self.stdout.write("Successfully un-set all due dates")
