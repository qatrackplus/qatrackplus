from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_comments.models import Comment

from qatrack.faults import admin, forms, views
from qatrack.faults.models import Fault, FaultType
from qatrack.qa.tests import utils
from qatrack.qatrack_core.dates import format_datetime
from qatrack.units import models as u_models


class TestFaultType:
    def test_str(self):
        assert str(FaultType(code="code")) == "code"


class TestFault(TestCase):

    def test_str(self):
        assert str(Fault(pk=1)) == "Fault ID: 1"


class TestFaultAdmin(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")

    def test_name(self):
        site = AdminSite()
        adm = admin.FaultAdmin(Fault, site)
        il = Fault(pk=1)
        assert adm.name(il) == str(il)

    def test_modality_filter_lookups(self):
        Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )


class TestModalityFilter(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        u_models.Modality.objects.all().delete()
        self.modality = utils.create_modality(name="modality")

        self.adm = admin.FaultAdmin(Fault, AdminSite())
        self.mf = admin.ModalityFilter(mock.Mock(), {}, Fault, self.adm)

    def test_modality_filter_lookups(self):
        assert list(self.mf.lookups(None, None)) == [(self.modality.pk, self.modality.name)]

    def test_filter(self):
        """If user filters by modality, only faults with that modality should be returned"""
        Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )
        correct_modality = Fault.objects.create(
            unit=self.unit,
            modality=self.modality,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
        )
        with mock.patch.object(self.mf, "value", return_value=self.modality.id):
            qs = self.mf.queryset(None, Fault.objects.all())
            assert list(qs) == [correct_modality]

    def test_no_filter(self):
        """If there is no modality filter, all faults should be returned"""
        Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )
        Fault.objects.create(
            unit=self.unit,
            modality=self.modality,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
        )
        with mock.patch.object(self.mf, "value", return_value=None):
            qs = self.mf.queryset(None, Fault.objects.all())
            assert list(qs) == list(Fault.objects.all())


class TestFaultManager(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")

    def test_unreviewed(self):
        """Two Faults created, only the unreviewed should be returned by the unreviewed manager"""

        Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )
        unreviewed = Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
        )
        assert Fault.objects.unreviewed().count() == 1
        assert Fault.objects.unreviewed().all()[0].pk == unreviewed.pk


class TestFaultList(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        self.url = reverse("fault_list")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def create_fault(self):

        Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )

    def test_load_page(self):
        """Initial page load should work ok"""
        self.create_fault()
        resp = self.client.get(self.url, {})
        assert resp.status_code == 200

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        self.create_fault()
        resp = self.client.get(self.url, {}, content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert len(resp.json()['aaData']) == 1

    def test_get_fields_one_site(self):
        """Only a single site, so unit__site__name should not be in fields"""
        fields = views.FaultList().get_fields(None)
        assert "unit__site__name" not in fields

    def test_get_fields_multiple_sites(self):
        """More than one site so unit__site__name should be in fields"""
        site = utils.create_site()
        utils.create_unit(name="second unit", site=site)
        fields = views.FaultList().get_fields(None)
        assert "unit__site__name" in fields

    def test_get_filters_multiple_sites(self):
        """If more than one site exists, there should be a noneornull filter for Other sites"""
        site = utils.create_site()
        utils.create_unit(name="second unit", site=site)
        self.create_fault()
        filters = views.FaultList().get_filters('unit__site__name')
        assert filters == [('noneornull', 'Other')]


class TestCreateEditFault(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        self.create_url = reverse("fault_create")
        self.list_url = reverse("fault_list")
        self.ajax_url = reverse("fault_create_ajax")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def create_fault(self):

        return Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )

    def test_load_create_page(self):
        """Initial page load should work ok"""
        assert self.client.get(self.create_url, {}).status_code == 200

    def test_load_edit_page(self):
        """Initial page load should work ok"""
        assert self.client.get(self.create_url, {}).status_code == 200

    def test_valid_create(self):
        """Test that creating a fault with all options set works"""

        technique = u_models.TreatmentTechnique.objects.create(name='technique')
        ft = FaultType.objects.create(code="fault type")

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-treatment_technique": technique.pk,
            "fault-fault_type_field": ft.code,
            "fault-comment": "test comment",
        }

        resp = self.client.post(self.create_url, data)
        assert resp.status_code == 302
        assert resp.url == self.list_url
        assert Comment.objects.count() == 1

    def test_valid_create_new_fault_type(self):
        """Test that creating a fault with all options set works"""

        technique = u_models.TreatmentTechnique.objects.create(name='technique')

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-treatment_technique": technique.pk,
            "fault-fault_type_field": "%s%s" % (forms.NEW_FAULT_TYPE_MARKER, "fault type"),
            "fault-comment": "test comment",
        }

        FaultType.objects.all().delete()
        resp = self.client.post(self.create_url, data)
        assert FaultType.objects.count() == 1
        assert resp.status_code == 302
        assert resp.url == self.list_url
        assert Comment.objects.count() == 1

    def test_valid_edit(self):
        """Test that editing a fault and modifying a field works"""

        technique = u_models.TreatmentTechnique.objects.create(name='technique')

        FaultType.objects.create(code="fault type")

        fault = self.create_fault()
        assert fault.treatment_technique is None

        edit_url = reverse("fault_edit", kwargs={'pk': fault.pk})

        data = {
            "fault-occurred": format_datetime(fault.occurred),
            "fault-unit": fault.unit.id,
            "fault-modality": '',
            "fault-treatment_technique": technique.pk,
            "fault-fault_type_field": fault.fault_type.code,
            "fault-comment": "",
        }

        resp = self.client.post(edit_url, data)
        assert resp.status_code == 302
        fault.refresh_from_db()
        assert fault.treatment_technique == technique
        assert resp.url == self.list_url

    def test_create_ajax_valid(self):
        """Test that creating a fault via ajax (e.g. from perform test list instance page) works"""

        technique = u_models.TreatmentTechnique.objects.create(name='technique')
        ft = FaultType.objects.create(code="fault type")

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-treatment_technique": technique.pk,
            "fault-fault_type_field": ft.code,
            "fault-comment": "test comment",
        }

        resp = self.client.post(self.ajax_url, data=data)
        assert resp.status_code == 200
        assert not resp.json()['error']
        assert Comment.objects.count() == 1

    def test_create_ajax_invalid(self):
        """Test that creating a fault via ajax with missing field works"""

        technique = u_models.TreatmentTechnique.objects.create(name='technique')
        ft = FaultType.objects.create(code="fault type")

        data = {
            "fault-occurred": "",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-treatment_technique": technique.pk,
            "fault-fault_type_field": ft.code,
            "fault-comment": "test comment",
        }

        resp = self.client.post(self.ajax_url, data=data)
        assert resp.status_code == 200
        assert 'occurred' in resp.json()['errors']


class TestFaultTypeAutocomplete(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.url = reverse("fault_type_autocomplete")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_empty_query(self):
        """If no query provided, all fault types should be returned (and not a 'new' fault type)"""
        for i in range(3):
            FaultType.objects.create(code="ft %d" % i)
        assert len(self.client.get(self.url).json()['results']) == 3

    def test_query_doesnt_exist(self):
        """If query doesn't match any fault types, then only a new fault type should be returned"""
        for i in range(3):
            FaultType.objects.create(code="ft %d" % i)

        results = self.client.get(self.url, {'q': 'new'}).json()['results']
        assert len(results) == 1
        assert results[0] == {'id': '%snew' % forms.NEW_FAULT_TYPE_MARKER, 'text': "*new*"}

    def test_query_exact_match_only(self):
        """If query matches a fault types exactly, and is not a match for any
        others, then only the exact match should be returned"""

        fts = [FaultType.objects.create(code="ft %d" % i) for i in range(3)]
        results = self.client.get(self.url, {'q': 'ft 2'}).json()['results']
        assert results == [{'id': fts[2].code, 'text': fts[2].code}]

    def test_query_exact_match_plus_others(self):
        """If query matches a fault types exactly, plus matches others, all
        should be returned, but the exact match should be first"""

        FaultType.objects.create(code="ft 212"),
        FaultType.objects.create(code="ft 21"),
        FaultType.objects.create(code="ft 213"),

        results = self.client.get(self.url, {'q': 'ft 21'}).json()['results']
        assert results == [
            {'id': "ft 21", 'text': "ft 21"},
            {'id': "ft 212", 'text': "ft 212"},
            {'id': "ft 213", 'text': "ft 213"},
        ]


class TestFaultDetails(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def create_fault(self):
        return Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )

    def test_load_page(self):
        """Initial page load should work ok"""
        fault = self.create_fault()
        url = reverse("fault_details", kwargs={'pk': fault.pk})
        resp = self.client.get(url)
        assert resp.status_code == 200
        assert resp.context['fault'].id == fault.id


class TestFaultsByUnit(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def create_fault(self, unit=None):

        return Fault.objects.create(
            unit=unit or self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )

    def test_load_page(self):
        """Initial page load should work ok"""
        fault = self.create_fault()
        url = reverse("fault_list_by_unit", kwargs={'unit_number': fault.unit.number})
        resp = self.client.get(url, {})
        assert resp.status_code == 200
        assert resp.context['unit'].pk == fault.unit.pk
        assert resp.context['page_title'] == "Faults for: %s" % fault.unit.site_unit_name()

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        fault1 = self.create_fault()
        u2 = utils.create_unit()
        self.create_fault(unit=u2)
        url = reverse("fault_list_by_unit", kwargs={'unit_number': fault1.unit.number})
        resp = self.client.get(url, {}, content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert len(resp.json()['aaData']) == 1

    def test_get_fields(self):
        """Only a single site, so unit__site__name should not be in fields"""
        fields = views.FaultsByUnit().get_fields(None)
        assert "unit__site__name" not in fields
        assert "unit__name" not in fields


class TestFaultsByUnitFaultType(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def create_fault(self, fault_type=None):

        return Fault.objects.create(
            unit=self.unit,
            fault_type=fault_type or self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )

    def test_load_page(self):
        """Initial page load should work ok"""
        fault = self.create_fault()
        kwargs = {'unit_number': fault.unit.number, 'slug': fault.fault_type.slug}
        url = reverse("fault_list_by_unit_type", kwargs=kwargs)
        resp = self.client.get(url, {})
        assert resp.status_code == 200
        assert resp.context['unit'].pk == fault.unit.pk
        assert resp.context['fault_type'].pk == fault.fault_type.pk

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        fault1 = self.create_fault()
        ft = FaultType.objects.create(code="new ft")
        self.create_fault(fault_type=ft)
        kwargs = {'unit_number': fault1.unit.number, 'slug': fault1.fault_type.slug}
        url = reverse("fault_list_by_unit_type", kwargs=kwargs)
        resp = self.client.get(url, {}, content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert len(resp.json()['aaData']) == 1

    def test_get_fields(self):
        """Only a single site, so unit__site__name should not be in fields"""
        fields = views.FaultsByUnit().get_fields(None)
        assert "unit__site__name" not in fields
        assert "unit__name" not in fields
        assert "fault_type" not in fields


class TestFaultTypeList(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        self.url = reverse("fault_type_list")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def create_fault(self):

        Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )

    def test_load_page(self):
        """Initial page load should work ok"""
        self.create_fault()
        resp = self.client.get(self.url, {})
        assert resp.status_code == 200

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        self.create_fault()
        resp = self.client.get(self.url, {}, content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert len(resp.json()['aaData']) == 1


class TestFaultTypeDetails(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def create_fault(self):

        return Fault.objects.create(
            unit=self.unit,
            fault_type=self.fault_type,
            created_by=self.user,
            modified_by=self.user,
            reviewed_by=self.user,
            reviewed=timezone.now(),
        )

    def test_load_page(self):
        """Initial page load should work ok"""
        fault = self.create_fault()
        url = reverse("fault_type_details", kwargs={'slug': fault.fault_type.slug})
        resp = self.client.get(url, {})
        assert resp.status_code == 200

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        fault = self.create_fault()
        url = reverse("fault_type_details", kwargs={'slug': fault.fault_type.slug})
        resp = self.client.get(url, {}, content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert len(resp.json()['aaData']) == 1


class TestChooseUnitForViewFaults(TestCase):

    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_load_page(self):
        """Initial page load should work ok"""
        resp = self.client.get(reverse("fault_choose_unit"))
        assert resp.status_code == 200
