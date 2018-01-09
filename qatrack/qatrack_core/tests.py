import re

from django.contrib.sites.models import Site
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from qatrack.qa.tests import utils


class TestLoginViews(TestCase):

    def test_password_reset(self):
        """Test full cycle of password reset process"""
        Site.objects.all().update(domain="")
        u = utils.create_user()
        self.client.post(reverse("password_reset"), {'email': u.email})
        assert "Password reset" in mail.outbox[0].subject

        url = re.search("(?P<url>https?://[^\s]+)", mail.outbox[0].body).group("url")
        resp = self.client.get(url)
        resp = self.client.post(resp.url, {
            'new_password1': 'newpassword',
            'new_password2': 'newpassword',
        })
        assert resp.url == "/accounts/reset/done/"
