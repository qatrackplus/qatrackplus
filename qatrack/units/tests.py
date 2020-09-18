from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from qatrack.qa.tests import utils
from qatrack.units import models


class TestUnits(TestCase):

    def test_auto_set_number(self):
        ut = models.UnitType.objects.create(name="UT")
        models.Unit.objects.create(name="U1", type=ut, number=1, date_acceptance=timezone.now())
        u2 = models.Unit.objects.create(name="U2", type=ut, date_acceptance=timezone.now())
        assert u2.number == 2


class TestVendor(TestCase):

    def test_get_by_nk(self):
        v = utils.create_vendor()
        assert models.Vendor.objects.get_by_natural_key(v.name).pk == v.pk

    def test_nk(self):
        v = utils.create_vendor()
        assert v.natural_key() == (v.name,)

    def test_str(self):
        assert str(models.Vendor(name="vendor")) == "vendor"


class TestUnitClass(TestCase):

    def test_get_by_nk(self):

        uc = models.UnitClass.objects.create(name="uclass")
        assert uc.natural_key() == (uc.name,)

    def test_str(self):
        assert str(models.UnitClass(name="uclass")) == "uclass"


class TestSite:

    def test_str(self):
        assert str(models.Site(name="site")) == "site"


class TestUnitType(TestCase):

    def test_get_by_nk(self):
        ut = utils.create_unit_type()
        assert models.UnitType.objects.get_by_natural_key(
            ut.name, ut.model, vendor_name=ut.vendor.name).pk == ut.pk

    def test_nk(self):
        ut = utils.create_unit_type()
        assert ut.natural_key() == (ut.name, ut.model, ut.vendor.name)


class TestModality:

    def test_nk(self):
        assert models.Modality(name="modality").natural_key() == ("modality", )

    def test_str(self):
        assert str(models.Modality(name="modality")) == "modality"


class TestWeekDayCount:

    def test_uate_list(self):
        start = timezone.datetime(2019, 12, 9).date()
        end = timezone.datetime(2019, 12, 15).date()
        week = models.weekday_count(start, end, {})
        assert week == {
            'monday': 1,
            'tuesday': 1,
            'wednesday': 1,
            'thursday': 1,
            'friday': 1,
            'saturday': 1,
            'sunday': 1,
        }


class TestUnitAvailableTime(TestCase):

    def setUp(self):
        utils.create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')
        self.get_url = reverse('unit_available_time')
        self.post_url = reverse('handle_unit_available_time')
        self.delete_url = reverse('delete_schedules')
        utils.create_unit()
        utils.create_unit()
        utils.create_unit()

    def test_unit_available_time_change(self):

        response = self.client.get(self.get_url)
        dt = timezone.localtime(timezone.now()) + timezone.timedelta(days=7)
        timestamp = int((dt).timestamp() * 1000)
        unit_ids = [u.id for u in response.context['units']]

        data = {
            'units[]': unit_ids,
            'hours_monday': '08:00',
            'hours_tuesday': '_8:00',
            'hours_wednesday': '_8:00',
            'hours_thursday': '08:00',
            'hours_friday': '08:00',
            'hours_saturday': '08:00',
            'hours_sunday': '08:00',
            'day': timestamp,
            'days[]': [timestamp],
            'tz': "utc",
        }

        init_hours = timezone.timedelta(hours=1)
        models.UnitAvailableTime.objects.create(
            unit=models.Unit.objects.first(),
            date_changed=dt,
            hours_monday=init_hours,
            hours_tuesday=init_hours,
            hours_wednesday=init_hours,
            hours_thursday=init_hours,
            hours_friday=init_hours,
            hours_saturday=init_hours,
            hours_sunday=init_hours,
        )

        date = timezone.localtime(timezone.datetime.fromtimestamp(timestamp / 1000, timezone.utc)).date()
        len_uat_before = len(models.UnitAvailableTime.objects.filter(unit_id__in=unit_ids, date_changed=date))

        self.client.post(self.post_url, data=data)
        len_uat_after = len(models.UnitAvailableTime.objects.filter(unit_id__in=unit_ids, date_changed=date))
        self.assertEqual(len(unit_ids), len_uat_after - len_uat_before + 1)

        self.client.post(self.delete_url, data=data)
        len_uat_after = len(models.UnitAvailableTime.objects.filter(unit_id__in=unit_ids, date_changed=date))
        self.assertEqual(0, len_uat_after)


class TestUnitAvailableTimeEdit(TestCase):

    def setUp(self):
        utils.create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')
        self.get_url = reverse('unit_available_time')
        self.post_url = reverse('handle_unit_available_time_edit')
        self.delete_url = reverse('delete_schedules')
        utils.create_unit()
        utils.create_unit()
        utils.create_unit()

    def test_handle_unit_available_time_edit(self):

        response = self.client.get(self.get_url)

        timestamp = int((timezone.localtime(timezone.now()) + timezone.timedelta(days=7)).timestamp() * 1000)
        unit_ids = [u.id for u in response.context['units']]

        data = {
            'units[]': unit_ids,
            'hours_mins': '_8:00',
            'days[]': [timestamp],
            'name': 'uate_test',
            'tz': "utc",
        }

        date = timezone.localtime(timezone.datetime.fromtimestamp(timestamp / 1000, timezone.utc)).date()
        len_uate_before = len(models.UnitAvailableTimeEdit.objects.filter(unit_id__in=unit_ids, date=date))
        self.client.post(self.post_url, data=data)
        len_uate_after = len(models.UnitAvailableTimeEdit.objects.filter(unit_id__in=unit_ids, date=date))
        self.assertEqual(len(unit_ids), len_uate_after - len_uate_before)

        self.client.post(self.delete_url, data=data)
        len_uate_after = len(models.UnitAvailableTimeEdit.objects.filter(unit_id__in=unit_ids, date=date))
        self.assertEqual(0, len_uate_after)

    def test_handle_unit_available_time_edit_prior_to_acceptance(self):

        response = self.client.get(self.get_url)
        models.Unit.objects.all().update(date_acceptance=timezone.now() + timezone.timedelta(days=30))

        timestamp = int((timezone.localtime(timezone.now()) + timezone.timedelta(days=7)).timestamp() * 1000)
        unit_ids = [u.id for u in response.context['units']]

        data = {
            'units[]': unit_ids,
            'hours_mins': '_8:00',
            'days[]': [timestamp],
            'name': 'uate_test',
            'tz': "utc",
        }

        date = timezone.localtime(timezone.datetime.fromtimestamp(timestamp / 1000, timezone.utc)).date()
        self.client.post(self.post_url, data=data)
        len_uate_after = len(models.UnitAvailableTimeEdit.objects.filter(unit_id__in=unit_ids, date=date))
        assert len_uate_after == 0

    def test_handle_unit_available_time_edit_existing(self):

        response = self.client.get(self.get_url)

        timestamp = int((timezone.localtime(timezone.now()) + timezone.timedelta(days=7)).timestamp() * 1000)
        unit_ids = [u.id for u in response.context['units']]

        data = {
            'units[]': unit_ids,
            'hours_mins': '_8:00',
            'days[]': [timestamp],
            'name': 'uate_test',
            'tz': "utc",
        }

        date = timezone.localtime(timezone.datetime.fromtimestamp(timestamp / 1000, timezone.utc)).date()
        len_uate_before = len(models.UnitAvailableTimeEdit.objects.filter(unit_id__in=unit_ids, date=date))

        self.client.post(self.post_url, data=data)
        len_uate_after = len(models.UnitAvailableTimeEdit.objects.filter(unit_id__in=unit_ids, date=date))
        self.assertEqual(len(unit_ids), len_uate_after - len_uate_before)

        data['hours_mins'] = '_2:00'
        self.client.post(self.post_url, data=data)
        len_uate_after_updated = len(models.UnitAvailableTimeEdit.objects.filter(unit_id__in=unit_ids, date=date))
        assert len_uate_after_updated == len_uate_after
        assert models.UnitAvailableTimeEdit.objects.first().hours == timezone.timedelta(hours=2)
