from typing import Union, Optional
from django.utils import timezone
from django.utils.text import slugify

from qatrack.qatrack_core.tests.utils import get_next_id
from qatrack.units.models import (
    Modality,
    ELECTRON,
    PHOTON,
    Room,
    Site,
    Storage,
    Unit,
    UnitClass,
    UnitType,
    UnitAvailableTime,
    UnitAvailableTimeEdit,
    Vendor,
)


def create_modality(energy: Union[int, float] = 6, particle: Union[PHOTON, ELECTRON] = PHOTON,
                    name: Optional[str] = None) -> Modality:

    if name is None:
        if particle == "photon":
            unit, particle = "MV", "Photon"
        else:
            unit, particle = "MeV", "Electron"
        a_name = "%g%s %s" % (energy, unit, particle)
    else:
        a_name = name
    m, _ = Modality.objects.get_or_create(name=a_name)
    return m


def create_vendor(name=None):

    if name is None:
        name = 'vendor_%04d' % get_next_id(Vendor.objects.order_by('id').last())

    v, _ = Vendor.objects.get_or_create(name=name)

    return v


def create_unit_class(name=None):

    if name is None:
        name = 'unit_class_%04d' % get_next_id(UnitClass.objects.order_by('id').last())

    uc, _ = UnitClass.objects.get_or_create(name=name)

    return uc


def create_unit_type(name=None, vendor=None, model="model", unit_class=None):

    if name is None:
        name = 'unit_type_%04d' % get_next_id(UnitType.objects.order_by('id').last())
    if vendor is None:
        vendor = create_vendor()

    if unit_class is None:
        unit_class = create_unit_class()

    ut, _ = UnitType.objects.get_or_create(name=name, vendor=vendor, model=model, unit_class=unit_class)
    ut.save()
    return ut


def create_site(name=None):

    if name is None:
        name = 'site_%04d' % get_next_id(Site.objects.order_by('id').last())

    slug = slugify(name)

    return Site.objects.create(name=name, slug=slug)


def create_unit(name=None, number=None, tipe=None, site=None, active=True, serviceable=True):

    if name is None:
        name = 'unit_%04d' % get_next_id(Unit.objects.order_by('id').last())
    if number is None:
        last = Unit.objects.order_by('number').last()
        number = last.number + 1 if last else 0
    if tipe is None:
        tipe = create_unit_type()
    if site is None:
        site = create_site()

    u = Unit(
        name=name,
        number=number,
        date_acceptance=timezone.now(),
        type=tipe,
        is_serviceable=serviceable,
        site=site,
        active=active,
    )
    u.save()
    u.modalities.add(create_modality())
    return u


def create_storage(room=None, location='shelf', quantity=1):

    if room is None:
        room = create_room()

    s, _ = Storage.objects.get_or_create(room=room, location=location)

    return s


def create_room(site=None, name=None):

    if name is None:
        name = 'room_%04d' % get_next_id(Room.objects.order_by('id').last())
    if site is None:
        site = create_site()

    r, _ = Room.objects.get_or_create(name=name, site=site)

    return r


def create_unit_available_time(unit=None, hours_per_day=8, date_changed=None):
    unit = unit or create_unit()
    date_changed = date_changed or unit.date_acceptance
    if isinstance(date_changed, timezone.datetime):
        date_changed = date_changed.date()
    hours_per_day = timezone.timedelta(hours=hours_per_day)
    return UnitAvailableTime.objects.create(
        unit=unit,
        date_changed=date_changed,
        hours_sunday=hours_per_day,
        hours_monday=hours_per_day,
        hours_tuesday=hours_per_day,
        hours_wednesday=hours_per_day,
        hours_thursday=hours_per_day,
        hours_friday=hours_per_day,
        hours_saturday=hours_per_day,
    )


def create_unit_available_time_edit(unit=None, hours=8, date=None, name="reason"):

    unit = unit or create_unit()
    date = date or timezone.now().date()
    hours = timezone.timedelta(hours=hours)

    return UnitAvailableTimeEdit.objects.create(
        unit=unit,
        name=name,
        date=date,
        hours=hours,
    )
