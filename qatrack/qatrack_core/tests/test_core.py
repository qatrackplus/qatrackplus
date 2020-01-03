import re

from django.contrib.sites.models import Site
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
import numpy as np
import pandas as pd
import pytz

from qatrack.qa.tests import utils
from qatrack.qatrack_core.serializers import QATrackJSONEncoder
from qatrack.qatrack_core.utils import end_of_day, relative_dates, start_of_day


class TestLoginViews(TestCase):

    def test_password_reset(self):
        """Test full cycle of password reset process"""
        Site.objects.all().update(domain="")
        u = utils.create_user()
        self.client.post(reverse("password_reset"), {'email': u.email})
        assert "Password reset" in mail.outbox[0].subject

        url = re.search(r"(?P<url>https?://[^\s]+)", mail.outbox[0].body).group("url")
        resp = self.client.get(url)
        resp = self.client.post(
            resp.url, {
                'new_password1': '8P0Cut!v6XUr',
                'new_password2': '8P0Cut!v6XUr',
            }, follow=True
        )
        assert "/accounts/reset/done/" in resp.redirect_chain[0]


class TestJSONEncoder:

    def test_np_int(self):
        enc = QATrackJSONEncoder()
        assert enc.default(np.int8(1)) == 1

    def test_np_array(self):
        enc = QATrackJSONEncoder()
        assert enc.default(np.array(range(3))) == [0, 1, 2]

    def test_range(self):
        enc = QATrackJSONEncoder()
        assert enc.default(range(3)) == [0, 1, 2]

    def test_zip(self):
        enc = QATrackJSONEncoder()
        assert enc.default(zip(range(3), range(3))) == [(0, 0), (1, 1), (2, 2)]

    def test_set(self):
        enc = QATrackJSONEncoder()
        assert set(enc.default(set(range(3)))) == set(range(3))

    def test_pd_df(self):
        enc = QATrackJSONEncoder()
        d = {'col1': [1, 2], 'col2': [3, 4]}
        df = pd.DataFrame(data=d)
        expected = {'col1': {0: 1, 1: 2}, 'col2': {0: 3, 1: 4}}
        assert enc.default(df) == expected


class TestRelativeDates:

    def setup_class(self):
        self.tz = pytz.timezone("America/Toronto")
        self.now = timezone.datetime(2020, 1, 2, 11, 38, tzinfo=self.tz)
        self.day_start = start_of_day(self.now)

    def test_next_7_days(self):
        r = relative_dates("next 7 days", self.now)
        end = end_of_day(timezone.datetime(2020, 1, 9, tzinfo=self.tz))
        assert r.start() == self.day_start
        assert r.end() == end

    def test_next_30_days(self):
        end = end_of_day(timezone.datetime(2020, 2, 1, tzinfo=self.tz))
        r = relative_dates("next 30 days", self.now)
        assert r.start() == self.day_start
        assert r.end() == end

    def test_next_365_days(self):
        end = end_of_day(timezone.datetime(2021, 1, 1, tzinfo=self.tz))
        r = relative_dates("next 365 days", self.now)
        assert r.start() == self.day_start
        assert r.end() == end

    def test_next_week(self):
        start = start_of_day(timezone.datetime(2020, 1, 5, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 11, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("next week", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_next_week_sat(self):
        pivot = timezone.datetime(2020, 1, 11, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2020, 1, 12, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 18, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("next week", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_next_week_sun(self):
        pivot = timezone.datetime(2020, 1, 12, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2020, 1, 19, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 25, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("next week", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_next_month(self):
        start = start_of_day(timezone.datetime(2020, 2, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 2, 29, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("next month", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_next_month_first_day(self):
        pivot = timezone.datetime(2020, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2020, 2, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 2, 29, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("next month", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_next_month_last_day(self):
        pivot = timezone.datetime(2020, 1, 31, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2020, 2, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 2, 29, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("next month", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_next_year(self):
        start = start_of_day(timezone.datetime(2021, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2021, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("next year", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_this_week(self):
        start = start_of_day(timezone.datetime(2019, 12, 29, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 4, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("this week", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_this_week_sat(self):
        pivot = timezone.datetime(2020, 1, 11, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2020, 1, 5, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 11, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("this week", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_this_week_sun(self):
        pivot = timezone.datetime(2020, 1, 5, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2020, 1, 5, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 11, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("this week", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_this_year(self):
        start = start_of_day(timezone.datetime(2020, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("this year", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_this_year_jan_1(self):
        pivot = timezone.datetime(2020, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2020, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("this year", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_this_year_dec_31(self):
        pivot = timezone.datetime(2020, 12, 31, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2020, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("this year", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_last_7_days(self):
        start = start_of_day(timezone.datetime(2019, 12, 26, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 2, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last 7 days", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_last_30_days(self):
        start = start_of_day(timezone.datetime(2019, 12, 3, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 2, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last 30 days", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_last_365_days(self):
        start = start_of_day(timezone.datetime(2019, 1, 2, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 2, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last 365 days", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_this_month(self):
        start = start_of_day(timezone.datetime(2020, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("this month", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_last_week(self):
        start = start_of_day(timezone.datetime(2019, 12, 22, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2019, 12, 28, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last week", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_last_week_sat(self):
        pivot = timezone.datetime(2020, 1, 4, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2019, 12, 22, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2019, 12, 28, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last week", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_last_week_sun(self):
        pivot = timezone.datetime(2020, 1, 5, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2019, 12, 29, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2020, 1, 4, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last week", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_last_month(self):
        start = start_of_day(timezone.datetime(2019, 12, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2019, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last month", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_last_month_jan1(self):
        pivot = timezone.datetime(2020, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2019, 12, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2019, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last month", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_last_month_jan31(self):
        pivot = timezone.datetime(2020, 1, 31, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2019, 12, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2019, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last month", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_last_year(self):
        start = start_of_day(timezone.datetime(2019, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2019, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last year", self.now)
        assert r.start() == start
        assert r.end() == end

    def test_last_year_jan1(self):
        pivot = timezone.datetime(2020, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2019, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2019, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last year", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_last_year_dec31(self):
        pivot = timezone.datetime(2020, 12, 31, 11, 38, tzinfo=pytz.timezone("America/Toronto"))
        start = start_of_day(timezone.datetime(2019, 1, 1, 11, 38, tzinfo=pytz.timezone("America/Toronto")))
        end = end_of_day(timezone.datetime(2019, 12, 31, tzinfo=pytz.timezone("America/Toronto")))
        r = relative_dates("last year", pivot)
        assert r.start() == start
        assert r.end() == end

    def test_today(self):

        start = self.day_start
        end = end_of_day(start)
        r = relative_dates("today", self.now)
        assert r.start() == start
        assert r.end() == end
