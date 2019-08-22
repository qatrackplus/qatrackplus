import re

from django.contrib.sites.models import Site
from django.core import mail
from django.test import TestCase
from django.urls import reverse
import numpy as np
import pandas as pd

from qatrack.qa.tests import utils
from qatrack.qatrack_core.serializers import QATrackJSONEncoder


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
                'new_password1': 'newpassword',
                'new_password2': 'newpassword',
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
