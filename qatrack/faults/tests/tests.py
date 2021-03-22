from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django_comments.models import Comment

from qatrack.faults import admin, forms, views
from qatrack.faults.models import Fault, FaultType, FaultReviewGroup, can_review_faults
from qatrack.faults.tests import utils
from qatrack.qa.tests import utils as qa_utils
from qatrack.qatrack_core.dates import format_datetime
from qatrack.service_log.tests import utils as sl_utils
from qatrack.units import models as u_models


class TestFaultType:
    def test_str(self):
        assert str(FaultType(code="code")) == "code"


class TestFault(TestCase):

    def test_str(self):
        assert str(Fault(pk=1)) == "Fault ID: 1"

    def test_get_absolute_url(self):
        fault = utils.create_fault()
        assert fault.get_absolute_url() == "/faults/%d/" % fault.pk

    def test_review_details_no_reviews_no_review_groups(self):
        fault = utils.create_fault()
        assert fault.review_details() == []

    def test_review_details_no_review_groups(self):
        review = utils.create_fault_review(review_group=False)
        assert review.fault.review_details() == [(None, review.reviewed_by, review.reviewed, False)]

    def test_review_complete_required_not_complete(self):
        utils.create_fault_review_group()
        rg_not_required = utils.create_fault_review_group(required=False)
        review = utils.create_fault_review(review_group=rg_not_required)
        assert not review.fault.review_complete()

    def test_review_complete_required_complete(self):
        rg_required = utils.create_fault_review_group()
        utils.create_fault_review_group(required=False)
        review = utils.create_fault_review(review_group=rg_required)
        assert review.fault.review_complete()


class TestCanReviewFaults(TestCase):

    def test_no_review_groups(self):

        user = qa_utils.create_user()
        p = Permission.objects.get(name="Can review faults")
        user.user_permissions.add(p)
        assert can_review_faults(user)

    def test_with_review_groups_no_perm(self):
        utils.create_fault_review_group()
        user = qa_utils.create_user()
        assert not can_review_faults(user)

    def test_with_review_groups_with_perm(self):
        frg = utils.create_fault_review_group()
        user = qa_utils.create_user()
        p = Permission.objects.get(name="Can review faults")
        user.user_permissions.add(p)
        user.groups.add(frg.group)
        assert can_review_faults(user)


class TestFaultAdmin(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")

    def test_name(self):
        site = AdminSite()
        adm = admin.FaultAdmin(Fault, site)
        il = Fault(pk=1)
        assert adm.name(il) == str(il)

    def test_modality_filter_lookups(self):
        site = AdminSite()
        adm = admin.FaultAdmin(Fault, site)
        modality = u_models.Modality.objects.create(name="modality")
        lookups = admin.ModalityFilter(None, {}, Fault, adm).lookups(None, adm)
        assert list(lookups) == [(modality.pk, modality.name)]

    def test_get_fault_types(self):
        ft1 = utils.create_fault_type()
        ft2 = utils.create_fault_type()
        fault = utils.create_fault(fault_type=[ft1, ft2])
        site = AdminSite()
        adm = admin.FaultAdmin(Fault, site)
        assert adm.get_fault_types(fault) == ', '.join(sorted([ft1.code, ft2.code]))


class TestModalityFilter(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        u_models.Modality.objects.all().delete()
        self.modality = qa_utils.create_modality(name="modality")

        self.adm = admin.FaultAdmin(Fault, AdminSite())
        self.mf = admin.ModalityFilter(mock.Mock(), {}, Fault, self.adm)

    def test_modality_filter_lookups(self):
        assert list(self.mf.lookups(None, None)) == [(self.modality.pk, self.modality.name)]

    def test_filter(self):
        """If user filters by modality, only faults with that modality should be returned"""

        f = utils.create_fault(unit=self.unit, user=self.user, fault_type=self.fault_type)

        correct_modality = utils.create_fault(
            unit=self.unit, user=self.user, fault_type=f.fault_types.first(), modality=self.modality)

        with mock.patch.object(self.mf, "value", return_value=self.modality.id):
            qs = self.mf.queryset(None, Fault.objects.all())
            assert list(qs) == [correct_modality]

    def test_no_filter(self):
        """If there is no modality filter, all faults should be returned"""
        utils.create_fault(unit=self.unit, user=self.user, fault_type=self.fault_type)
        utils.create_fault(unit=self.unit, user=self.user, fault_type=self.fault_type)
        with mock.patch.object(self.mf, "value", return_value=None):
            qs = self.mf.queryset(None, Fault.objects.all())
            assert list(qs) == list(Fault.objects.all())


class TestFaultManager(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")

    def test_unreviewed(self):
        """Two Faults created, only the unreviewed should be returned by the unreviewed manager"""

        utils.create_fault_review()
        unreviewed = utils.create_fault()

        assert Fault.objects.unreviewed().count() == 1
        assert Fault.objects.unreviewed().all()[0].pk == unreviewed.pk


class TestFaultList(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        self.url = reverse("fault_list")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_load_page(self):
        """Initial page load should work ok"""
        utils.create_fault()
        resp = self.client.get(self.url, {})
        assert resp.status_code == 200

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        utils.create_fault()
        resp = self.client.get(self.url, {}, content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert len(resp.json()['aaData']) == 1

    def test_get_fields_one_site(self):
        """Only a single site, so unit__site__name should not be in fields"""
        fields = views.FaultList().get_fields(None)
        assert "unit__site__name" not in fields

    def test_get_fields_multiple_sites(self):
        """More than one site so unit__site__name should be in fields"""
        site = qa_utils.create_site()
        qa_utils.create_unit(name="second unit", site=site)
        fields = views.FaultList().get_fields(None)
        assert "unit__site__name" in fields

    def test_get_filters_multiple_sites(self):
        """If more than one site exists, there should be a noneornull filter for Other sites"""
        site = qa_utils.create_site()
        qa_utils.create_unit(name="second unit", site=site)
        utils.create_fault()
        filters = views.FaultList().get_filters('unit__site__name')
        assert filters == [('noneornull', 'Other')]


class TestUnreviewedFaultList(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        self.url = reverse("fault_list_unreviewed")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_get_queryset(self):
        utils.create_fault()
        qs = views.UnreviewedFaultList().get_queryset().all()
        assert qs.count() == 1

    @override_settings(BULK_REVIEW=True)
    def test_get_fields_with_bulk(self):
        assert 'selected' in views.UnreviewedFaultList().get_fields()

    def test_selected(self):
        fault = utils.create_fault()
        assert ('data-fault="%d"' % fault.id) in views.UnreviewedFaultList().selected(fault)

    def test_page_title(self):
        resp = self.client.get(self.url)
        assert resp.context['page_title'] == "Unreviewed Faults"


class TestCRUDFault(TestCase):

    def setUp(self):
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        self.create_url = reverse("fault_create")
        self.list_url = reverse("fault_list")
        self.ajax_url = reverse("fault_create_ajax")
        self.user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(self.user)

    def test_load_create_page(self):
        """Initial page load should work ok"""
        assert self.client.get(self.create_url, {}).status_code == 200

    def test_load_edit_page(self):
        """Initial page load should work ok"""
        assert self.client.get(self.create_url, {}).status_code == 200

    def test_valid_create(self):
        """Test that creating a fault with all options set works"""

        ft = FaultType.objects.create(code="fault type")

        usa = sl_utils.create_unit_service_area(unit=self.unit)
        se = sl_utils.create_service_event(unit_service_area=usa)

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": [ft.code],
            "fault-comment": "test comment",
            "fault-related_service_events": [se.pk],
        }

        resp = self.client.post(self.create_url, data)
        assert resp.status_code == 302
        assert resp.url == self.list_url
        assert Comment.objects.count() == 1
        assert list(Fault.objects.latest('pk').related_service_events.values_list("id", flat=True)) == [se.id]

    def test_valid_create_with_review(self):
        """Test that creating a fault with all options and a reviewer set works"""

        ft = FaultType.objects.create(code="fault type")

        rev_group = utils.create_fault_review_group()
        self.user.groups.add(rev_group.group)

        usa = sl_utils.create_unit_service_area(unit=self.unit)
        se = sl_utils.create_service_event(unit_service_area=usa)

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": [ft.code],
            "fault-comment": "test comment",
            "fault-related_service_events": [se.pk],
            "review-form-0-group": rev_group.group.name,
            "review-form-0-reviewed_by": self.user.pk,
        }

        resp = self.client.post(self.create_url, data)
        assert resp.status_code == 302
        assert resp.url == self.list_url
        assert Comment.objects.count() == 1
        f = Fault.objects.latest('pk')
        assert f.faultreviewinstance_set.count() == 1
        assert list(f.related_service_events.values_list("id", flat=True)) == [se.id]

    def test_valid_create_with_invalid_review(self):
        """Test that creating a fault with all options and an invalid reviewer does not work"""

        ft = FaultType.objects.create(code="fault type")

        rev_group = utils.create_fault_review_group()
        self.user.groups.add(rev_group.group)

        usa = sl_utils.create_unit_service_area(unit=self.unit)
        se = sl_utils.create_service_event(unit_service_area=usa)

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": [ft.code],
            "fault-comment": "test comment",
            "fault-related_service_events": [se.pk],
            "review-form-0-group": rev_group.group.name,
            "review-form-0-reviewed_by": "",
        }

        resp = self.client.post(self.create_url, data)
        assert resp.status_code == 200
        assert resp.context['review_forms'][0].errors

    def test_valid_create_with_no_reviewers(self):
        """Test that creating a fault with all options and an no reviewers works if review group is not required"""

        ft = FaultType.objects.create(code="fault type")

        rev_group = utils.create_fault_review_group(required=False)
        self.user.groups.add(rev_group.group)

        usa = sl_utils.create_unit_service_area(unit=self.unit)
        se = sl_utils.create_service_event(unit_service_area=usa)

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": [ft.code],
            "fault-comment": "test comment",
            "fault-related_service_events": [se.pk],
            "review-form-0-group": rev_group.group.name,
            "review-form-0-reviewed_by": "",
        }

        resp = self.client.post(self.create_url, data)
        assert resp.status_code == 302

    def test_dont_include_related(self):
        assert 'related_service_events' not in forms.FaultForm(include_related_ses=False).fields

    def test_invalid_create(self):
        """Test that trying to create a fault with no unit doesn't work"""

        ft = FaultType.objects.create(code="fault type")

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": '',
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": [ft.code],
            "fault-comment": "test comment",
        }

        resp = self.client.post(self.create_url, data)
        assert resp.status_code == 200
        assert 'unit' in resp.context['form'].errors

    def test_valid_create_new_fault_type(self):
        """Test that creating a fault with all options set works"""

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": ["%s%s" % (forms.NEW_FAULT_TYPE_MARKER, "fault type")],
            "fault-comment": "test comment",
        }

        FaultType.objects.all().delete()
        resp = self.client.post(self.create_url, data)
        assert FaultType.objects.count() == 1
        assert resp.status_code == 302
        assert resp.url == self.list_url
        assert Comment.objects.count() == 1

    def test_valid_create_new_fault_type_multiple(self):
        """Test that creating a fault with all options set works"""

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": [
                "%s%s" % (forms.NEW_FAULT_TYPE_MARKER, "fault type 1"),
                "%s%s" % (forms.NEW_FAULT_TYPE_MARKER, "fault type 2"),
            ],
            "fault-comment": "test comment",
        }

        FaultType.objects.all().delete()
        resp = self.client.post(self.create_url, data)
        assert FaultType.objects.count() == 2
        assert resp.status_code == 302
        assert resp.url == self.list_url
        assert Comment.objects.count() == 1

    def test_valid_edit_load(self):
        """Test that editing a fault and modifying a field works"""

        FaultType.objects.create(code="fault type")

        fault = utils.create_fault()

        edit_url = reverse("fault_edit", kwargs={'pk': fault.pk})
        se = sl_utils.create_service_event()
        fault.related_service_events.add(se)

        resp = self.client.get(edit_url)
        assert resp.status_code == 200

    def test_valid_edit(self):
        """Test that editing a fault and modifying a field works"""

        FaultType.objects.create(code="fault type")

        fault = utils.create_fault()
        assert fault.modality is None

        modality = u_models.Modality.objects.create(name="modality")
        fault.unit.modalities.add(modality)

        edit_url = reverse("fault_edit", kwargs={'pk': fault.pk})
        se = sl_utils.create_service_event()
        fault.related_service_events.add(se)

        data = {
            "fault-occurred": format_datetime(fault.occurred),
            "fault-unit": fault.unit.id,
            "fault-modality": modality.pk,
            "fault-fault_types_field": [fault.fault_types.first().code],
            "fault-comment": "",
            "fault-related_service_events": [se.pk],
        }

        resp = self.client.post(edit_url, data)
        assert resp.status_code == 302
        fault.refresh_from_db()
        assert fault.modality == modality
        assert resp.url == self.list_url

    def test_invalid_edit(self):
        """Test that editing a fault and modifying a field works"""

        modality = u_models.Modality.objects.create(name="modality")

        FaultType.objects.create(code="fault type")

        fault = utils.create_fault()
        assert fault.modality is None

        edit_url = reverse("fault_edit", kwargs={'pk': fault.pk})
        se = sl_utils.create_service_event()
        fault.related_service_events.add(se)

        data = {
            "fault-occurred": format_datetime(fault.occurred),
            "fault-unit": '',
            "fault-modality": modality.pk,
            "fault-fault_types_field": [fault.fault_types.first().code],
            "fault-comment": "",
            "fault-related_service_events": [se.pk],
        }

        resp = self.client.post(edit_url, data)
        assert resp.status_code == 200

    def test_edit_with_new_reviews(self):
        """Test that editing a fault and adding a reviewer works"""

        FaultType.objects.create(code="fault type")

        fault = utils.create_fault(user=self.user)
        rev_group = utils.create_fault_review_group()
        self.user.groups.add(rev_group.group)
        assert fault.modality is None

        modality = u_models.Modality.objects.create(name="modality")
        fault.unit.modalities.add(modality)

        edit_url = reverse("fault_edit", kwargs={'pk': fault.pk})
        se = sl_utils.create_service_event()
        fault.related_service_events.add(se)

        data = {
            "fault-occurred": format_datetime(fault.occurred),
            "fault-unit": fault.unit.id,
            "fault-modality": modality.pk,
            "fault-fault_types_field": [fault.fault_types.first().code],
            "fault-comment": "",
            "fault-related_service_events": [se.pk],
            "review-form-0-group": rev_group.group.name,
            "review-form-0-reviewed_by": fault.created_by.pk,
        }

        assert fault.faultreviewinstance_set.count() == 0
        resp = self.client.post(edit_url, data)
        assert resp.status_code == 302
        fault.refresh_from_db()
        assert fault.faultreviewinstance_set.count() == 1
        assert fault.modality == modality
        assert resp.url == self.list_url

    def test_edit_with_invalid_reviews(self):
        """Test that editing a fault and adding a reviewer works"""

        FaultType.objects.create(code="fault type")

        fault = utils.create_fault(user=self.user)
        rev_group = utils.create_fault_review_group()
        self.user.groups.add(rev_group.group)
        assert fault.modality is None

        modality = u_models.Modality.objects.create(name="modality")
        fault.unit.modalities.add(modality)

        edit_url = reverse("fault_edit", kwargs={'pk': fault.pk})
        se = sl_utils.create_service_event()
        fault.related_service_events.add(se)

        data = {
            "fault-occurred": format_datetime(fault.occurred),
            "fault-unit": fault.unit.id,
            "fault-modality": modality.pk,
            "fault-fault_types_field": [fault.fault_types.first().code],
            "fault-comment": "",
            "fault-related_service_events": [se.pk],
            "review-form-0-group": rev_group.group.name,
            "review-form-0-reviewed_by": "",
        }

        assert fault.faultreviewinstance_set.count() == 0
        resp = self.client.post(edit_url, data)
        assert resp.status_code == 200
        assert resp.context['review_forms'][0].errors['reviewed_by']

    def test_edit_with_existing_reviews(self):
        """Test that editing a fault with existing reviewer works"""

        FaultType.objects.create(code="fault type")

        fault = utils.create_fault(user=self.user)
        rev_group = utils.create_fault_review_group()
        utils.create_fault_review(fault=fault, review_group=rev_group, reviewed_by=self.user)
        self.user.groups.add(rev_group.group)
        assert fault.modality is None

        modality = u_models.Modality.objects.create(name="modality")
        fault.unit.modalities.add(modality)

        edit_url = reverse("fault_edit", kwargs={'pk': fault.pk})
        se = sl_utils.create_service_event()
        fault.related_service_events.add(se)

        data = {
            "fault-occurred": format_datetime(fault.occurred),
            "fault-unit": fault.unit.id,
            "fault-modality": modality.pk,
            "fault-fault_types_field": [fault.fault_types.first().code],
            "fault-comment": "",
            "fault-related_service_events": [se.pk],
            "review-form-0-group": rev_group.group.name,
            "review-form-0-reviewed_by": fault.created_by.pk,
        }

        assert fault.faultreviewinstance_set.count() == 1
        resp = self.client.post(edit_url, data)
        assert resp.status_code == 302
        fault.refresh_from_db()
        assert fault.faultreviewinstance_set.count() == 1
        assert fault.modality == modality
        assert resp.url == self.list_url

    def test_edit_with_changed_reviews(self):
        """Test that editing a fault with existing reviewer works"""

        FaultType.objects.create(code="fault type")

        fault = utils.create_fault(user=self.user)
        rev_group = utils.create_fault_review_group()
        utils.create_fault_review(fault=fault, review_group=rev_group, reviewed_by=self.user)
        self.user.groups.add(rev_group.group)
        new_u = qa_utils.create_user()
        new_u.groups.add(rev_group.group)

        modality = u_models.Modality.objects.create(name="modality")
        fault.unit.modalities.add(modality)

        edit_url = reverse("fault_edit", kwargs={'pk': fault.pk})
        se = sl_utils.create_service_event()
        fault.related_service_events.add(se)

        data = {
            "fault-occurred": format_datetime(fault.occurred),
            "fault-unit": fault.unit.id,
            "fault-modality": modality.pk,
            "fault-fault_types_field": [fault.fault_types.first().code],
            "fault-comment": "",
            "fault-related_service_events": [se.pk],
            "review-form-0-group": rev_group.group.name,
            "review-form-0-reviewed_by": new_u.pk,
        }

        assert list(fault.faultreviewinstance_set.values_list("reviewed_by_id", flat=True)) == [self.user.pk]
        resp = self.client.post(edit_url, data)
        assert resp.status_code == 302
        fault.refresh_from_db()
        assert fault.faultreviewinstance_set.count() == 1
        assert list(fault.faultreviewinstance_set.values_list("reviewed_by_id", flat=True)) == [new_u.pk]

    def test_edit_with_removed_reviews(self):
        """Test that editing a fault with existing reviewer works"""

        FaultType.objects.create(code="fault type")

        fault = utils.create_fault(user=self.user)
        rev_group = utils.create_fault_review_group(required=False)
        utils.create_fault_review(fault=fault, review_group=rev_group, reviewed_by=self.user)
        self.user.groups.add(rev_group.group)

        modality = u_models.Modality.objects.create(name="modality")
        fault.unit.modalities.add(modality)

        edit_url = reverse("fault_edit", kwargs={'pk': fault.pk})
        se = sl_utils.create_service_event()
        fault.related_service_events.add(se)

        data = {
            "fault-occurred": format_datetime(fault.occurred),
            "fault-unit": fault.unit.id,
            "fault-modality": modality.pk,
            "fault-fault_types_field": [fault.fault_types.first().code],
            "fault-comment": "",
            "fault-related_service_events": [se.pk],
            "review-form-0-group": rev_group.group.name,
            "review-form-0-reviewed_by": "",
        }

        assert list(fault.faultreviewinstance_set.values_list("reviewed_by_id", flat=True)) == [self.user.pk]
        resp = self.client.post(edit_url, data)
        assert resp.status_code == 302
        fault.refresh_from_db()
        assert fault.faultreviewinstance_set.count() == 0

    def test_create_ajax_valid(self):
        """Test that creating a fault via ajax (e.g. from perform test list instance page) works"""

        ft = FaultType.objects.create(code="fault type")

        data = {
            "fault-occurred": "20 Jan 2021 17:59",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": [ft.code],
            "fault-comment": "test comment",
        }

        resp = self.client.post(self.ajax_url, data=data)
        assert resp.status_code == 200
        assert not resp.json()['error']
        assert Comment.objects.count() == 1

    def test_create_ajax_invalid(self):
        """Test that creating a fault via ajax with missing field works"""

        ft = FaultType.objects.create(code="fault type")

        data = {
            "fault-occurred": "",
            "fault-unit": self.unit.id,
            "fault-modality": self.unit.modalities.all().first().pk,
            "fault-fault_types_field": [ft.code],
            "fault-comment": "test comment",
        }

        resp = self.client.post(self.ajax_url, data=data)
        assert resp.status_code == 200
        assert 'occurred' in resp.json()['errors']

    def test_valid_delete(self):
        """Test that deleting a fault works"""

        fault = utils.create_fault()
        delete_url = reverse("fault_delete", kwargs={'pk': fault.pk})
        se = sl_utils.create_service_event()
        fault.related_service_events.add(se)
        resp = self.client.post(delete_url)
        assert resp.status_code == 302
        assert resp.url == '/faults/'
        assert Fault.objects.count() == 0

    def test_review_fault(self):
        fault = utils.create_fault()
        review_url = reverse("fault_review", kwargs={'pk': fault.pk})
        resp = self.client.post(review_url)
        assert resp.status_code == 302
        assert fault.faultreviewinstance_set.first() is not None

    def test_unreview_fault(self):
        fault = utils.create_fault_review().fault
        review_url = reverse("fault_review", kwargs={'pk': fault.pk})
        resp = self.client.post(review_url)
        assert resp.status_code == 302
        fault.refresh_from_db()
        assert fault.faultreviewinstance_set.first() is None

    def test_review_bulk(self):
        group = qa_utils.create_group("group")
        self.user.groups.add(group)
        frg = FaultReviewGroup.objects.create(group=group)

        f1 = utils.create_fault()
        f2 = utils.create_fault()
        review_url = reverse("fault_bulk_review")
        data = {'faults': [f1.pk, f2.pk]}
        resp = self.client.post(review_url, data=data)
        assert resp.status_code == 200
        assert resp.json()['ok']
        f1.refresh_from_db()
        f2.refresh_from_db()
        assert f1.faultreviewinstance_set.count() > 0
        assert f1.faultreviewinstance_set.first().fault_review_group == frg
        assert f2.faultreviewinstance_set.count() > 0


class TestFaultTypeAutocomplete(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
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
        expected = {'id': '%snew' % forms.NEW_FAULT_TYPE_MARKER, 'text': "*new*", 'code': 'new', 'description': ''}
        assert results[0] == expected

    def test_query_exact_match_only(self):
        """If query matches a fault types exactly, and is not a match for any
        others, then only the exact match should be returned"""

        fts = [FaultType.objects.create(code="ft %d" % i) for i in range(3)]
        results = self.client.get(self.url, {'q': 'ft 2'}).json()['results']
        expected = [{
            'id': fts[2].code,
            'text': "ft 2",
            'code': fts[2].code,
            'description': ''
        }]
        assert results == expected

    def test_query_exact_match_plus_others(self):
        """If query matches a fault types exactly, plus matches others, all
        should be returned, but the exact match should be first"""

        FaultType.objects.create(code="ft 212", description="description"),
        FaultType.objects.create(code="ft 21"),
        FaultType.objects.create(code="ft 213"),

        results = self.client.get(self.url, {'q': 'ft 21'}).json()['results']
        assert results == [
            {'id': "ft 21", 'text': "ft 21", 'code': "ft 21", 'description': ''},
            {'id': "ft 212", 'text': "ft 212: description", 'code': "ft 212", 'description': 'description'},
            {'id': "ft 213", 'text': "ft 213", 'code': "ft 213", 'description': ''},
        ]


class TestFaultDetails(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_load_page(self):
        """Initial page load should work ok"""
        fault_type = FaultType.objects.create(code="ABC", slug="abc")
        fault = utils.create_fault(fault_type=fault_type)
        url = reverse("fault_details", kwargs={'pk': fault.pk})
        resp = self.client.get(url)
        assert resp.status_code == 200
        assert resp.context['fault'].id == fault.id

    def test_queryset_fault_superset(self):
        """get_queryset should return all faults which have one or more faults
        in common with the current fault"""

        ft1 = FaultType.objects.create(code="A", slug="a")
        ft2 = FaultType.objects.create(code="B", slug="b")
        ft3 = FaultType.objects.create(code="C", slug="c")
        f1 = utils.create_fault(fault_type=[ft1, ft2, ft3])
        f2 = utils.create_fault(fault_type=[ft2])
        f3 = utils.create_fault(fault_type=[ft3])

        from django.test import RequestFactory

        url = reverse("fault_details", kwargs={'pk': f1.pk})
        req = RequestFactory().get(url, pk=f1.pk)
        req.user = self.user
        view = views.FaultDetails()
        view.kwargs = {'pk': f1.pk}
        qs = list(view.get_queryset())
        assert all(f in qs for f in [f1, f2, f3])


class TestFaultsByUnit(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_load_page(self):
        """Initial page load should work ok"""
        fault = utils.create_fault()
        url = reverse("fault_list_by_unit", kwargs={'unit_number': fault.unit.number})
        resp = self.client.get(url, {})
        assert resp.status_code == 200
        assert resp.context['unit'].pk == fault.unit.pk
        assert resp.context['page_title'] == "Faults for: %s" % fault.unit.site_unit_name()

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        fault1 = utils.create_fault()
        u2 = qa_utils.create_unit()
        utils.create_fault(unit=u2)
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
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_load_page(self):
        """Initial page load should work ok"""
        fault = utils.create_fault()
        kwargs = {'unit_number': fault.unit.number, 'slug': fault.fault_types.first().slug}
        url = reverse("fault_list_by_unit_type", kwargs=kwargs)
        resp = self.client.get(url, {})
        assert resp.status_code == 200
        assert resp.context['unit'].pk == fault.unit.pk
        assert resp.context['fault_type'].pk == fault.fault_types.first().pk

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        fault1 = utils.create_fault()
        ft = FaultType.objects.create(code="new ft")
        utils.create_fault(fault_type=ft)
        kwargs = {'unit_number': fault1.unit.number, 'slug': fault1.fault_types.first().slug}
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
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        self.url = reverse("fault_type_list")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_load_page(self):
        """Initial page load should work ok"""
        utils.create_fault()
        resp = self.client.get(self.url, {})
        assert resp.status_code == 200

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        utils.create_fault(fault_type=self.fault_type)
        resp = self.client.get(self.url, {}, content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert len(resp.json()['aaData']) == 1


class TestFaultTypeDetails(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_load_page(self):
        """Initial page load should work ok"""
        fault = utils.create_fault(fault_type=self.fault_type)
        url = reverse("fault_type_details", kwargs={'slug': fault.fault_types.first().slug})
        resp = self.client.get(url, {})
        assert resp.status_code == 200

    def test_load_result_set(self):
        """Calling via ajax should return a single object in the queryset"""
        fault = utils.create_fault(fault_type=self.fault_type)
        url = reverse("fault_type_details", kwargs={'slug': fault.fault_types.first().slug})
        resp = self.client.get(url, {}, content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert len(resp.json()['aaData']) == 1


class TestChooseUnitForViewFaults(TestCase):

    def setUp(self):
        self.user = qa_utils.create_user()
        self.unit = qa_utils.create_unit()
        self.fault_type = FaultType.objects.create(code="ABC", slug="abc")
        user = User.objects.create_superuser("faultuser", "a@b.com", "password")
        self.client.force_login(user)

    def test_load_page(self):
        """Initial page load should work ok"""
        resp = self.client.get(reverse("fault_choose_unit"))
        assert resp.status_code == 200
