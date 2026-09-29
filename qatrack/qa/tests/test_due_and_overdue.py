"""B27: "Due & Overdue QC" omitted everything due later today.

`due_date` is a `DateTimeField`. The view compared it against a `date`, so Django
coerced that to a naive midnight datetime and warned about it:

    RuntimeWarning: DateTimeField UnitTestCollection.due_date received a naive
    datetime (2026-09-28 00:00:00) while time zone support is active.

The cutoff was therefore *today at 00:00*. A collection due today at 09:00 was
absent from the page all day.

The Due Dates *report* (`reports/qc/due_dates.py`) has always used
`end_of_day(timezone.now())`, so the page and the report answered the same
question differently. These tests pin the page to the report's behaviour, and one
of them asserts the two agree directly.
"""

import datetime as dt

from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from qatrack.qa import models
from qatrack.qa.tests import utils
from qatrack.qa.views.perform import DueAndOverdue
from qatrack.qatrack_core.dates import end_of_day


def at(day_offset, hour, minute=0):
    tz = timezone.get_current_timezone()
    day = timezone.localtime(timezone.now()).date() + dt.timedelta(days=day_offset)
    return dt.datetime.combine(day, dt.time(hour, minute), tzinfo=tz)


class TestDueAndOverdueIncludesEverythingDueToday(TestCase):

    def setUp(self):
        # The base queryset narrows by `visible_to__in=user.groups`, so a user in
        # no group sees nothing whatever the due dates are - that is B2/#883, and
        # without this the tests below fail for the wrong reason. The factory adds
        # every existing group to `visible_to`, so the group has to exist first.
        from django.contrib.auth.models import Group

        self.group, _ = Group.objects.get_or_create(name='group')
        self.user = utils.create_user(is_superuser=True)
        self.user.groups.add(self.group)
        self.unit = utils.create_unit()
        test_list = utils.create_test_list()
        utils.create_test_list_membership(test_list, utils.create_test())

        self.cases = {}
        for label, when in [
            ('yesterday_2300', at(-1, 23, 0)),
            ('today_0000', at(0, 0, 0)),
            ('today_0900', at(0, 9, 0)),
            ('today_2359', at(0, 23, 59)),
            ('tomorrow_0000', at(1, 0, 0)),
            ('tomorrow_0900', at(1, 9, 0)),
        ]:
            utc = utils.create_unit_test_collection(unit=self.unit, test_collection=test_list)
            models.UnitTestCollection.objects.filter(pk=utc.pk).update(due_date=when)
            self.cases[label] = utc.pk

    def listed(self):
        request = RequestFactory().get('/qc/due-and-overdue/')
        request.user = self.user
        view = DueAndOverdue()
        view.request = request
        view.kwargs = {}
        return set(view.get_queryset().values_list('pk', flat=True))

    def test_something_due_earlier_today_is_listed(self):
        """The defect. It was absent all day, every day."""

        assert self.cases['today_0900'] in self.listed()

    def test_something_due_at_the_very_end_of_today_is_listed(self):
        assert self.cases['today_2359'] in self.listed()

    def test_something_due_at_midnight_today_is_listed(self):
        """This one worked before, and must keep working."""

        assert self.cases['today_0000'] in self.listed()

    def test_something_overdue_is_listed(self):
        assert self.cases['yesterday_2300'] in self.listed()

    def test_nothing_due_tomorrow_is_listed(self):
        """The boundary has moved by a day, not been removed."""

        listed = self.listed()
        assert self.cases['tomorrow_0000'] not in listed
        assert self.cases['tomorrow_0900'] not in listed

    def test_a_collection_with_no_due_date_is_not_listed(self):
        utc = utils.create_unit_test_collection(unit=self.unit)
        models.UnitTestCollection.objects.filter(pk=utc.pk).update(due_date=None)
        assert utc.pk not in self.listed()

    def test_the_page_and_the_due_dates_report_now_agree(self):
        """
        They disagreed, which is what made the bug easy to miss: the same
        question asked two ways gave two answers.
        """

        report_qs = models.UnitTestCollection.objects.filter(
            due_date__lte=end_of_day(timezone.now())
        ).exclude(due_date=None)
        assert self.listed() == set(report_qs.values_list('pk', flat=True))

    def test_no_naive_datetime_warning_is_raised(self):
        """
        The RuntimeWarning was the symptom Django offered, and it is how this was
        found. It must not come back.
        """

        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            self.listed()

        naive = [w for w in caught if 'naive datetime' in str(w.message)]
        assert naive == [], [str(w.message) for w in naive]
