"""A review is stamped from the site's clock, not the machine's.

`review_test_list_instance` used to build its timestamp by attaching Django's
zone to `datetime.now()`, which reads the machine's wall clock. Django points
the process at `settings.TIME_ZONE` only where `time.tzset` exists - see the
comment at `django/conf/__init__.py`, *"we don't do this unconditionally
(breaks Windows)"* - so on Windows the two can differ, and a review was then
stamped with a correct-looking local time carrying the wrong zone. It also
picked the first of a repeated hour when the clocks went back.

**This test exists because the rest of the coverage cannot see that.**
`qatrack_core/tests/test_naive_datetimes.py` is a pattern guard: it reads the
source and fails on `datetime.now()`. That stops the mistake coming back by
the same spelling, and says nothing about whether the timestamp is right.
@nsmela asked for the behavioural half on q#926 and wrote the first version of
this; it measured a review stamped 14 hours out on `develop`.

Two things about the shape, since both are easy to get wrong.

**It skips where `time.tzset` is missing, which is the platform the defect
affects.** That looks backwards and is not: the test's method is to move the
process clock away from `TIME_ZONE`, and on Windows there is no way to do that
from Python. A Windows run would raise `AttributeError` on `time.tzset`
instead of testing anything, so it says why it skipped rather than erroring in
every Windows and SQL Server row of CI.

**The process clock is global**, so the zone is restored in a `finally` even if
the assertion fails. A leaked `TZ` would change what every test after this one
sees, and the failure would land somewhere unrelated.

It is a `TestCase` and not a `TransactionTestCase` deliberately. The function
under test writes rows, which a transaction-wrapped case handles perfectly
well, and every `TransactionTestCase` added to this suite truncates tables
without restoring what the migrations created - the order dependence recorded
as B229, which a shuffled run reaches through all seven
`TestServiceEventReviewEmails` tests. Adding another one for no gain would make
that worse.
"""

import os
import time

import pytest
from django.test import TestCase
from django.utils import timezone

from qatrack.qa.tests import utils
from qatrack.qa.views.review import review_test_list_instance

# Far enough from any North American zone that a wrong answer cannot be
# mistaken for clock skew: Tokyo is UTC+9 with no daylight saving, so against
# America/Toronto the error is 13 or 14 hours depending on the season.
ELSEWHERE = 'Asia/Tokyo'

# Generous, because the point is a timestamp hours out rather than seconds. A
# tight bound would turn a slow machine into a failure and say nothing more.
TOLERANCE_SECONDS = 60

needs_tzset = pytest.mark.skipif(
    not hasattr(time, 'tzset'),
    reason=(
        "no time.tzset on this platform, so the process clock cannot be moved away "
        "from TIME_ZONE here. That absence is the reason the defect only ever showed "
        "on Windows - see this module's docstring."
    ),
)


class MachineClock:
    """Put the process clock in another zone, and put it back afterwards."""

    def __init__(self, zone):
        self.zone = zone
        self.previous = None

    def __enter__(self):
        self.previous = os.environ.get('TZ')
        os.environ['TZ'] = self.zone
        time.tzset()
        return self

    def __exit__(self, *exc):
        if self.previous is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = self.previous
        time.tzset()
        return False


@needs_tzset
class TestAReviewIsStampedFromTheSiteClock(TestCase):

    def setUp(self):
        self.status = utils.create_status()
        self.test_list_instance = utils.create_test_list_instance()
        self.test_instance = utils.create_test_instance(self.test_list_instance)

    def review(self):
        review_test_list_instance(
            self.test_list_instance,
            [self.test_instance],
            [self.status.pk],
            self.test_list_instance.created_by,
        )
        self.test_list_instance.refresh_from_db()
        return self.test_list_instance.reviewed

    def test_the_review_time_is_now_even_when_the_machine_is_elsewhere(self):
        with MachineClock(ELSEWHERE):
            reviewed = self.review()
            drift = abs((reviewed - timezone.now()).total_seconds())

        assert drift < TOLERANCE_SECONDS, (
            "the review was stamped %.1f hours from now with the machine clock in %s. "
            "The timestamp is being taken from the machine's wall clock and labelled "
            "with the site's zone, so it is wrong by the difference between them."
            % (drift / 3600.0, ELSEWHERE)
        )

    def test_the_process_clock_is_put_back(self):
        """Otherwise this module quietly breaks whatever runs after it."""
        before = os.environ.get('TZ')
        with MachineClock(ELSEWHERE):
            assert os.environ['TZ'] == ELSEWHERE, 'the context manager did not take effect'
        assert os.environ.get('TZ') == before, (
            'TZ was left at %r instead of %r' % (os.environ.get('TZ'), before)
        )

    def test_the_review_time_is_also_right_with_no_zone_shift(self):
        """The control: the assertion must not pass merely because it is loose."""
        drift = abs((self.review() - timezone.now()).total_seconds())
        assert drift < TOLERANCE_SECONDS, (
            'the review is stamped %.1f s from now with no clock shift at all, so this '
            'module is measuring something other than the zone' % drift
        )
