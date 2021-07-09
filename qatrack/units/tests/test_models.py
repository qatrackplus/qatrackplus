from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from qatrack.units import models
from qatrack.units.tests import utils as u_utils


class TestUnits(TestCase):

    def test_auto_set_number(self):
        """Ensure a unit created without an explicit number will get the next
        avaialble number assigned to it"""

        ut = u_utils.create_unit_type()
        site = models.Site.objects.create(name="site", slug="site")
        models.Unit.objects.create(name="U1", type=ut, number=1, site=site, date_acceptance=timezone.now())
        u2 = models.Unit.objects.create(name="U2", type=ut, date_acceptance=timezone.now(), site=site)
        assert u2.number == 2

    def test_str(self):
        assert str(models.Unit(name="unit")) == "unit"

    def test_site_unit_name(self):
        s = u_utils.create_site(name="s")
        u = u_utils.create_unit(name="u", site=s)
        assert u.site_unit_name() == "s :: u"

    def test_get_potential_time_no_available_time(self):
        """When no available time, get_potential_time should return 0"""
        u = u_utils.create_unit()
        now = timezone.datetime(2021, 7, 9, 12, 0, tzinfo=timezone.utc)
        acceptance = now - timezone.timedelta(days=2)
        u.date_acceptance = acceptance
        u.save()
        assert u.get_potential_time(None, now) == 0

    def test_get_potential_time_8hrs_per_day(self):
        """3 days (Jul 7, Jul 8, Jul 9) of 8 hours available should return 24 total hours of available time"""

        acceptance = timezone.datetime(2021, 7, 7, 12, 0, tzinfo=timezone.utc).date()
        now = timezone.datetime(2021, 7, 9, 12, 0, tzinfo=timezone.utc).date()
        u = u_utils.create_unit()
        u.date_acceptance = acceptance
        u.save()

        u_utils.create_unit_available_time(unit=u, hours_per_day=8)
        assert u.get_potential_time(None, now) == 24

    def test_get_potential_time_8hrs_per_day_with_8hr_edit(self):
        """3 days (Jul 7, Jul 8, Jul 9) of 8 hours available with 0hr edit
        should return 16 total hours of available time"""

        acceptance = timezone.datetime(2021, 7, 7, 12, 0, tzinfo=timezone.utc).date()
        edit_date = timezone.datetime(2021, 7, 8, 12, 0, tzinfo=timezone.utc).date()
        now = timezone.datetime(2021, 7, 9, 12, 0, tzinfo=timezone.utc).date()
        u = u_utils.create_unit()
        u.date_acceptance = acceptance
        u.save()

        u_utils.create_unit_available_time(unit=u, hours_per_day=8)
        u_utils.create_unit_available_time_edit(unit=u, hours=0, date=edit_date)
        assert u.get_potential_time(None, now) == 16

    def test_get_potential_time_before_acceptance(self):
        """if both dates are before acceptance, 0 hours of potential time"""

        acceptance = timezone.datetime(2021, 7, 7, 12, 0, tzinfo=timezone.utc).date()
        u = u_utils.create_unit()
        u.date_acceptance = acceptance
        u.save()

        d1 = timezone.datetime(1999, 12, 31).date()
        d2 = timezone.datetime(1999, 12, 31).date()

        u_utils.create_unit_available_time(unit=u, hours_per_day=8)
        assert u.get_potential_time(d1, d2) == 0

    def test_get_potential_time_8hrs_per_day_straddle_acceptance(self):
        """2 days (Jul 7, Jul 8, Jul 9) after acceptance of 8 hours available
        should return 16 total hours of available time"""

        date_from = timezone.datetime(2021, 7, 7, 12, 0, tzinfo=timezone.utc).date()
        acceptance = timezone.datetime(2021, 7, 8, 12, 0, tzinfo=timezone.utc).date()
        now = timezone.datetime(2021, 7, 9, 12, 0, tzinfo=timezone.utc).date()
        u = u_utils.create_unit()
        u.date_acceptance = acceptance
        u.save()

        u_utils.create_unit_available_time(unit=u, hours_per_day=8)
        assert u.get_potential_time(date_from, now) == 16


class TestVendor(TestCase):

    def test_get_by_nk(self):
        v = u_utils.create_vendor()
        assert models.Vendor.objects.get_by_natural_key(v.name).pk == v.pk

    def test_nk(self):
        v = u_utils.create_vendor()
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
        ut = u_utils.create_unit_type()
        assert models.UnitType.objects.get_by_natural_key(
            ut.name, ut.model, ut.unit_class.name, vendor_name=ut.vendor.name).pk == ut.pk

    def test_nk(self):
        ut = u_utils.create_unit_type()
        assert ut.natural_key() == (ut.name, ut.model, ut.vendor.name, ut.unit_class.name)

    def test_str(self):
        assert str(models.UnitType(name="ut", model="model")) == 'ut - model'


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


class TestRoomAndStorage(TestCase):

    def setUp(self):

        self.si_1 = u_utils.create_site(name="site 1")
        self.r_1 = u_utils.create_room(name='room 1', site=self.si_1)
        self.st_1 = u_utils.create_storage(room=self.r_1, location='top_shelf')

    def test_room_str(self):
        assert str(self.r_1) == "room 1 (site 1)"

    def test_storage_str(self):
        self.assertEqual(str(self.st_1), '%s - %s - %s' % (self.si_1.name, self.r_1.name, self.st_1.location))

    def test_storage_str_no_loc(self):
        s2 = u_utils.create_storage(location=None)
        assert str(s2) == "%s - %s - <no location>" % (s2.room.site.name, s2.room.name)

    def test_get_storage_qs_for_room(self):
        """Ensure only storages related to room are returned from queryset_for_room"""
        u_utils.create_storage()
        assert set(models.Storage.objects.get_queryset_for_room(self.r_1).all()) == set(self.r_1.storage_set.all())


class TestUnitAvailableTime(TestCase):

    def test_str_uat(self):
        assert str(models.UnitAvailableTime()) == "Available time schedule change"

    def test_str_aute(self):
        d1 = timezone.now().date()
        assert str(models.UnitAvailableTimeEdit(name="test", date=d1)) == "test (%s)" % models.fmt_date(d1)

    @override_settings(DEFAULT_AVAILABLE_TIMES={'hours_sunday': 8, 'hours_monday': 8})
    def test_available_times_on_unit_acceptance(self):
        u = u_utils.create_unit()
        u.date_acceptance = timezone.now().date()
        u.save()
        uat = models.UnitAvailableTime.available_times_on_unit_acceptance(u.id)
        assert uat.date_changed == u.date_acceptance


class TestGetUnitInfo(TestCase):

    def test_get_active_only(self):
        u1 = u_utils.create_unit(active=False)
        ui = models.get_unit_info(active_only=True)
        assert u1.pk not in ui

    def test_get_active_only_false(self):
        u1 = u_utils.create_unit(active=False)
        ui = models.get_unit_info(active_only=False)
        assert u1.pk in ui

    def test_get_serviceable_only(self):
        u1 = u_utils.create_unit(serviceable=False)
        ui = models.get_unit_info(serviceable_only=True)
        assert u1.pk not in ui

    def test_get_serviceable_only_false(self):
        u1 = u_utils.create_unit(serviceable=False)
        ui = models.get_unit_info(serviceable_only=False)
        assert u1.pk in ui

    def test_get_with_uids(self):
        u1 = u_utils.create_unit()
        u2 = u_utils.create_unit()
        ui = models.get_unit_info(unit_ids=[u1.pk])
        assert u1.pk in ui
        assert u2.pk not in ui
