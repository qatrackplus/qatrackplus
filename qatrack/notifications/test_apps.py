"""Every periodic task registered on post_migrate must name a real callable.

`do_scheduling()` registered
`service_log_scheduling.tasks.run_service_event_scheduling_notices`, which has
never existed - the function is `run_scheduling_notices`. Because
`_schedule_periodic_task()` overwrites `Schedule.func` on every `post_migrate`,
correcting the database row by hand was reverted by the next `migrate`, and the
task failed every ~15 minutes with `ValueError: Function ... is not defined`.

Nothing surfaced that in the application: the failure is visible only in the
Django Q cluster log and the `Failure` table, so scheduled service event notices
simply never went out. The typo arrived with the i18n commit `5258af6d`
(2025-08-19) and survived a year, because nothing resolved these strings until
Django Q tried to call one.

This asserts on the paths `do_scheduling()` actually registers, rather than on a
copy of the list, so a new entry is covered the moment it is added.
"""

from unittest import mock

from django.test import TestCase
from django.utils.module_loading import import_string

from qatrack.notifications.apps import do_scheduling


class TestPeriodicNotificationPaths(TestCase):

    def registered(self):
        """The (path, name) pairs do_scheduling() hands to the scheduler."""
        captured = []
        target = "qatrack.qatrack_core.tasks._schedule_periodic_task"
        with mock.patch(target, side_effect=lambda func, name: captured.append((func, name))):
            do_scheduling(sender=None)
        return captured

    def test_every_registered_path_imports_to_a_callable(self):
        registered = self.registered()
        assert registered, "do_scheduling() registered nothing"

        for path, name in registered:
            try:
                func = import_string(path)
            except ImportError as e:
                raise AssertionError(
                    "%r is registered as %r but does not exist: %s" % (name, path, e)
                )
            assert callable(func), "%s is not callable" % path

    def test_the_service_event_scheduling_notice_is_registered_once_and_correctly(self):
        """The specific regression, named so a failure says which task broke."""
        paths = dict((name, path) for path, name in self.registered())
        assert paths["QATrack+ Service Event Scheduling Notices"] == (
            "qatrack.notifications.service_log_scheduling.tasks.run_scheduling_notices"
        )

    def test_names_are_unique(self):
        """`_schedule_periodic_task` keys on the name, so a duplicate silently wins."""
        names = [name for _, name in self.registered()]
        assert len(names) == len(set(names)), names
