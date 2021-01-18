from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.utils import timezone

from qatrack.faults import admin
from qatrack.faults.models import Fault, FaultType
from qatrack.qa.tests import utils
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
