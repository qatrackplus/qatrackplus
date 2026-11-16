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

**It puts the machine and the site in different zones in one of two ways,
because the platforms differ in which of the two Python can move.**

- **Where `time.tzset` exists**, Django points the process clock at
  `TIME_ZONE` whenever that setting changes, tests included, so changing the
  setting would move both. Instead the process clock is moved away from it
  (`MachineClock`).
- **On Windows there is no `time.tzset`**, so the process clock cannot be
  moved from Python - and for the same reason Django leaves it alone when
  `TIME_ZONE` changes. Moving `TIME_ZONE` with `override_settings` is then
  enough, and it is exactly the situation the defect needs: a site whose zone
  is not the machine's. Without this the test would skip on the one platform
  the defect affects.

On a machine that is already in `ELSEWHERE` neither way produces a
difference, so the test says so and skips rather than passing on nothing.

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

import datetime
import os
import time

import pytest
from django.test import TestCase, override_settings
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

HAS_TZSET = hasattr(time, 'tzset')

needs_tzset = pytest.mark.skipif(
    not HAS_TZSET,
    reason=(
        "no time.tzset on this platform, so there is no process clock to put back. "
        "The review tests still run here, by moving TIME_ZONE instead - see this "
        "module's docstring."
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


def machine_and_site_apart():
    """Put the machine's wall clock and TIME_ZONE in different zones, on any platform."""
    if HAS_TZSET:
        return MachineClock(ELSEWHERE)
    return override_settings(TIME_ZONE=ELSEWHERE)


def hours_between_machine_and_site():
    machine = datetime.datetime.now()
    site = timezone.localtime(timezone.now()).replace(tzinfo=None)
    return abs((site - machine).total_seconds()) / 3600.0


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
        with machine_and_site_apart():
            if hours_between_machine_and_site() < 1:
                pytest.skip('this machine is already in %s, so the zones cannot be put apart' % ELSEWHERE)
            reviewed = self.review()
            drift = abs((reviewed - timezone.now()).total_seconds())

        assert drift < TOLERANCE_SECONDS, (
            "the review was stamped %.1f hours from now with the %s in %s. "
            "The timestamp is being taken from the machine's wall clock and labelled "
            "with the site's zone, so it is wrong by the difference between them."
            % (drift / 3600.0, 'machine clock' if HAS_TZSET else 'site (TIME_ZONE)', ELSEWHERE)
        )

    @needs_tzset
    def test_the_process_clock_is_put_back(self):
        """Otherwise this module quietly breaks whatever runs after it."""
        before = os.environ.get('TZ')
        with MachineClock(ELSEWHERE):
            assert os.environ['TZ'] == ELSEWHERE, 'the context manager did not take effect'
        assert os.environ.get('TZ') == before, (
            'TZ was left at %r instead of %r' % (os.environ.get('TZ'), before)
        )

    def test_the_review_time_is_also_right_with_no_zone_shift(self):
        """The control: the assertion must not pass merely because it is loose.

        On Windows this can fail on the defect itself, with nothing moved: the
        machine keeps its own zone, so a machine that is not in TIME_ZONE is
        already a site elsewhere. The message says which case it is.
        """
        apart = hours_between_machine_and_site()
        drift = abs((self.review() - timezone.now()).total_seconds())
        assert drift < TOLERANCE_SECONDS, (
            'the review is stamped %.1f s from now with no zone moved by this test. %s'
            % (
                drift,
                'This machine is %.1f h from TIME_ZONE already, so that is the defect itself.' % apart
                if apart >= 1
                else 'The machine is in TIME_ZONE, so this module is measuring something other than the zone.',
            )
        )
