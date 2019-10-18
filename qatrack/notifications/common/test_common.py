from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from qatrack.notifications.common import admin
from qatrack.notifications.common.models import (
    RecipientGroup,
    TestListGroup,
    UnitGroup,
)


class TestRecipientGroupModel:

    def test_sort_emails(self):
        rg = RecipientGroup(name="out of order", emails="b@a.com, a@b.com")
        rg._sort_emails()
        assert rg.emails == "a@b.com, b@a.com"

    def test_str(self):
        rg = RecipientGroup(name="name")
        assert str(rg) == "name"


class TestTestListGroupModel:

    def test_str(self):
        tlg = TestListGroup(name="name")
        assert str(tlg) == "name"


class TestUnitGroupModel:

    def test_str(self):
        ug = UnitGroup(name="name")
        assert str(ug) == "name"


class TestRecipientGroupAdmin(TestCase):

    def setUp(self):
        self.admin = admin.RecipientGroupAdmin(model=RecipientGroup, admin_site=AdminSite())
        self.rg = RecipientGroup.objects.create(name="RG")

    def test_clean_emails_valid(self):
        f = admin.RecipientGroupForm()
        f.cleaned_data = {'emails': 'b@a.com, a@b.com'}
        f.clean_emails()
        assert not f.errors

    def test_clean_emails_no_emails(self):
        f = admin.RecipientGroupForm()
        f.cleaned_data = {}
        f.clean_emails()
        assert not f.errors

    def test_clean_emails_invalid(self):
        f = admin.RecipientGroupForm()
        f.cleaned_data = {'emails': 'b@a.com blah, a@b.com'}
        f.clean_emails()
        assert "b@a.com blah" in f.errors['emails'][0]

    def test_get_groups(self):
        assert self.admin.get_groups(self.rg) == ""

    def test_get_users(self):
        assert self.admin.get_users(self.rg) == ""

    def test_get_emails(self):
        assert self.admin.get_emails(self.rg) == ""

    def test_clean_no_recipients(self):
        f = admin.RecipientGroupForm()
        f.cleaned_data = {}
        f.clean()
        assert '__all__' in f.errors


class TestTestListGroupAdmin(TestCase):

    def setUp(self):
        self.admin = admin.TestListGroupAdmin(model=TestListGroup, admin_site=AdminSite())
        self.tlg = TestListGroup.objects.create(name="TLG")

    def test_get_test_lists(self):
        assert self.admin.get_test_lists(self.tlg) == ""

    def test_form_queryset(self):
        f = admin.TestListGroupForm()
        assert f.fields['test_lists'].queryset.ordered


class TestUnitGroupAdmin(TestCase):

    def setUp(self):
        self.admin = admin.UnitGroupAdmin(model=UnitGroup, admin_site=AdminSite())
        self.ug = UnitGroup.objects.create(name="UG")

    def test_get_units(self):
        assert self.admin.get_units(self.ug) == ""
