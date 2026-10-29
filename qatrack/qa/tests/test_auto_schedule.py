"""`manage.py auto_schedule` must accept the actions it documents.

The command read its action from `handle(self, *args)` and defined no
`add_arguments`, so argparse had no positional argument to parse. Under Django 4.2
that makes every documented action a parse error:

    $ manage.py auto_schedule disable-all
    manage.py auto_schedule: error: unrecognized arguments: disable-all

    $ manage.py auto_schedule
    CommandError: Valid arguments are 'enable-all', 'disable-all', 'schedule-all', 'unschedule-all'

A closed loop: run it bare and it names four actions, pass any of them and the
parser refuses. All four are documented at `docs/admin/qa/auto_schedule.rst:16-47`,
so the whole command was unusable rather than partly broken.

The tests assert on `Command.ACTIONS` rather than on a copy of the four names, so a
fifth action is covered the moment it is added - the same approach
`notifications/test_apps.py` takes for the periodic task paths, and for the same
reason: a name that nothing resolves is invisible until something tries to use it.
"""

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

import qatrack.qa.tests.utils as utils
from qatrack.qa.management.commands.auto_schedule import Command
from qatrack.qa.models import UnitTestCollection


def run(action):
    """Call the command the way a user would, capturing its output."""
    out, err = StringIO(), StringIO()
    call_command("auto_schedule", action, stdout=out, stderr=err)
    return out.getvalue(), err.getvalue()


class TestTheActionsAreWiredUp(TestCase):
    """Guards for the class of bug this was: a name nothing resolves."""

    def test_actions_were_found_at_all(self):
        assert Command.ACTIONS, 'Command.ACTIONS is empty - has the dispatch moved?'

    def test_every_action_maps_to_a_method_that_exists(self):
        for action, method_name in Command.ACTIONS.items():
            method = getattr(Command, method_name, None)
            assert method is not None, (
                "%r dispatches to %r, which Command does not define" % (action, method_name)
            )
            assert callable(method), "%s is not callable" % method_name

    def test_the_parser_offers_exactly_the_actions_it_can_run(self):
        """`choices` and the dispatch come from one mapping; prove they agree."""
        parser = Command().create_parser('manage.py', 'auto_schedule')
        choices = [a.choices for a in parser._actions if a.dest == 'action']
        assert choices, 'the command defines no positional `action` argument'
        assert sorted(choices[0]) == sorted(Command.ACTIONS)

    def test_the_four_documented_actions_are_all_accepted(self):
        """docs/admin/qa/auto_schedule.rst documents these four by name."""
        documented = {'enable-all', 'disable-all', 'schedule-all', 'unschedule-all'}
        assert documented <= set(Command.ACTIONS), (
            'documented actions missing from the command: %r' % sorted(documented - set(Command.ACTIONS))
        )


class TestBadInputIsRejected(TestCase):

    def test_an_unrecognised_action_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command("auto_schedule", "no-such-action", stdout=StringIO(), stderr=StringIO())

    def test_omitting_the_action_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command("auto_schedule", stdout=StringIO(), stderr=StringIO())


class TestTheActionsDoTheirWork(TestCase):
    """The regression: before the fix none of these could run at all."""

    def setUp(self):
        self.scheduled = utils.create_unit_test_collection()
        self.unscheduled = utils.create_unit_test_collection(null_frequency=True)

    def refresh(self):
        self.scheduled.refresh_from_db()
        self.unscheduled.refresh_from_db()

    def test_enable_all_sets_auto_schedule_only_where_there_is_a_frequency(self):
        UnitTestCollection.objects.update(auto_schedule=False)
        out, _ = run("enable-all")
        self.refresh()
        assert self.scheduled.auto_schedule is True
        assert self.unscheduled.auto_schedule is False, (
            'an item with no frequency has nothing to schedule from, so enable-all '
            'must leave it alone'
        )
        assert 'enabled auto scheduling' in out

    def test_disable_all_clears_auto_schedule_everywhere(self):
        UnitTestCollection.objects.update(auto_schedule=True)
        out, _ = run("disable-all")
        self.refresh()
        assert self.scheduled.auto_schedule is False
        assert self.unscheduled.auto_schedule is False
        assert 'disabled auto scheduling' in out

    def test_schedule_all_visits_every_item_with_a_frequency(self):
        """Asserts which rows are visited rather than the date produced.

        `set_due_date()` derives the date through `calc_due_date()`, which depends
        on the item's history, so the value is not a fixed thing to assert. Which
        objects the command selects is the part this command decides.
        """
        with mock.patch.object(UnitTestCollection, 'set_due_date', autospec=True) as set_due:
            out, _ = run("schedule-all")
        visited = {call.args[0].pk for call in set_due.call_args_list}
        assert self.scheduled.pk in visited
        assert self.unscheduled.pk not in visited, (
            'an item with no frequency has no due date to compute'
        )
        assert 'set all due dates' in out

    def test_unschedule_all_clears_every_due_date(self):
        from django.utils import timezone
        UnitTestCollection.objects.update(due_date=timezone.now())
        out, _ = run("unschedule-all")
        self.refresh()
        assert self.scheduled.due_date is None
        assert self.unscheduled.due_date is None
        assert 'un-set all due dates' in out
