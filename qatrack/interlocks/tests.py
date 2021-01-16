from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from qatrack.interlocks import admin
from qatrack.interlocks.models import Interlock, InterlockType


class TestInterlockType:
    def test_str(self):
        assert str(InterlockType(code="code")) == "code"


class TestInterlock(TestCase):

    def test_str(self):
        assert str(Interlock(pk=1)) == "Interlock ID: 1"


class TestInterlockAdmin:

    def test_name(self):
        site = AdminSite()
        adm = admin.InterlockAdmin(Interlock, site)
        il = Interlock(pk=1)
        assert adm.name(il) == str(il)
