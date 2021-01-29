import calendar
from collections import defaultdict

from django.conf import settings
from django.db import models
from django.db.models.aggregates import Max
from django.utils.timezone import timedelta
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qatrack_core.dates import format_as_date as fmt_date

PHOTON = 'photon'
ELECTRON = 'electron'


class NameNaturalKeyManager(models.Manager):

    def get_by_natural_key(self, name):
        return self.get(name=name)


class Vendor(models.Model):
    """ Vendor of Unit

    Stores information (just name for now) of unit vendor.
    """

    name = models.CharField(
        verbose_name=_l("name"),
        max_length=64,
        unique=True,
        help_text=_l('Name of this vendor'),
    )
    notes = models.TextField(
        verbose_name=_l("notes"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_l('Additional notes about this vendor')
    )

    objects = NameNaturalKeyManager()

    class Meta:
        ordering = ("name",)
        verbose_name = _l("Vendor")
        verbose_name_plural = _l("Vendor")

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        """Display more descriptive name"""
        return self.name


class UnitClass(models.Model):
    """ Class of unit

    Unit class, ie. linac, CT, MR, etc.
    """

    name = models.CharField(
        verbose_name=_l("name"),
        max_length=64,
        unique=True,
        help_text=_l('Name of this unit class'),
    )

    objects = NameNaturalKeyManager()

    class Meta:
        verbose_name = _l("unit class")
        verbose_name_plural = _l("unit classes")
        ordering = ("name",)

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        """Display more descriptive name"""
        return self.name


class Site(models.Model):
    """ Site unit resides

    Allows for multiple site filtering (different campuses, buildings, hospitals, etc)
    """
    name = models.CharField(
        verbose_name=_l("name"),
        max_length=64,
        unique=True,
        help_text=_l('Name of this site'),
    )
    slug = models.SlugField(
        verbose_name=_l("slug"),
        max_length=50,
        help_text=_l("Unique identifier made of lowercase characters and underscores for this site"),
        unique=True,
    )

    class Meta:
        ordering = ("name",)
        verbose_name = _l("site")
        verbose_name_plural = _l("sites")

    def __str__(self):
        return self.name


class UnitTypeManager(models.Manager):

    def get_by_natural_key(self, name, model, vendor_name=None, unitclass_name=None):
        return self.get(name=name, model=model, vendor__name=vendor_name, unit_class__name=unitclass_name)


class UnitType(models.Model):
    """Radiation Device Type

    Stores a device type for grouping individual :model:`unit`s together.
    For example, your Elekta Linacs might form one group, and your Tomo's
    another.

    """
    vendor = models.ForeignKey(
        Vendor,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_l("vendor"),
    )

    unit_class = models.ForeignKey(
        UnitClass,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_l("unit class"),
    )

    name = models.CharField(
        verbose_name=_l("name"),
        max_length=50,
        help_text=_l('Name for this unit type'),
    )
    model = models.CharField(
        verbose_name=_l("model"),
        max_length=50,
        null=True,
        blank=True,
        help_text=_l('Optional model name for this group'),
    )

    collapse = models.BooleanField(
        verbose_name=_l("Collapse"),
        help_text=_l("Collapse this unit type in the user interface by default"),
        default=False,
    )

    objects = UnitTypeManager()

    class Meta:
        unique_together = [('name', 'model', 'vendor', 'unit_class',)]
        ordering = ("vendor__name", "name",)
        verbose_name = _l("unit type")
        verbose_name_plural = _l("unit types")

    def natural_key(self):
        vendor = self.vendor.natural_key() if self.vendor else ()
        unit_class = self.unit_class.natural_key() if self.unit_class else ()
        return (self.name, self.model) + vendor + unit_class
    natural_key.dependencies = ["units.vendor", "units.unitclass"]

    def __str__(self):
        """Display more descriptive name"""
        return '%s%s' % (self.name, ' - %s' % self.model if self.model else '')


class Modality(models.Model):
    """Treatment modalities

    defines available treatment modalities for a given :model:`unit1`

    """

    name = models.CharField(
        _l('Name'),
        max_length=255,
        help_text=_l('Descriptive name for this modality'),
        unique=True
    )

    objects = NameNaturalKeyManager()

    class Meta:
        verbose_name = _l("modality")
        verbose_name_plural = _l('modalities')

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name


class TreatmentTechnique(models.Model):

    name = models.CharField(
        verbose_name=_l("name"),
        max_length=255,
        unique=True,
        help_text=_l('Name of this treatment technique'),
    )

    objects = NameNaturalKeyManager()

    class Meta:
        verbose_name = _l("treatment technique")
        verbose_name_plural = _l("treatment techniques")
        ordering = ("name",)

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name


def weekday_count(start_date, end_date, uate_list):
    week = {}
    for i in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=i)
        if str(day) not in uate_list:
            day_name = calendar.day_name[day.weekday()].lower()
            week[day_name] = week[day_name] + 1 if day_name in week else 1
    return week


class Unit(models.Model):
    """Radiation devices
    Stores a single radiation device (e.g. Linac, Tomo unit, Cyberkinfe etc.)
    """
    type = models.ForeignKey(UnitType, verbose_name=_l("Unit Type"), on_delete=models.PROTECT)
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.PROTECT)

    number = models.PositiveIntegerField(
        null=False,
        blank=True,
        unique=True,
        help_text=_l('A unique number for this unit. Leave blank to have it assigned automatically'),
    )
    name = models.CharField(max_length=256, help_text=_l('The display name for this unit'))
    serial_number = models.CharField(max_length=256, null=True, blank=True, help_text=_l('Optional serial number'))
    location = models.CharField(max_length=256, null=True, blank=True, help_text=_l('Optional location information'))
    install_date = models.DateField(null=True, blank=True, help_text=_l('Optional install date'))
    date_acceptance = models.DateField(
        verbose_name=_l("Acceptance date"),
        help_text=_l('Changing acceptance date will delete unit available times that occur before it'),
    )
    active = models.BooleanField(default=True, help_text=_l('Set to false if unit is no longer in use'))
    # restricted = models.BooleanField(default=False, help_text=_l('Set to false to restrict unit from operation'))
    is_serviceable = models.BooleanField(
        default=True, help_text=_l('Set to true to enable this unit to be selectable in service events')
    )

    modalities = models.ManyToManyField(Modality)
    treatment_techniques = models.ManyToManyField(TreatmentTechnique)

    class Meta:
        ordering = [settings.ORDER_UNITS_BY]
        verbose_name = _l("unit")
        verbose_name_plural = _l('units')

    def __str__(self):
        return self.name

    def site_unit_name(self):
        return "%s :: %s" % (_("Other") if not self.site else self.site.name, self.name)

    def get_potential_time(self, date_from, date_to):

        if date_from is None:
            date_from = self.date_acceptance

        elif date_from < self.date_acceptance:
            if date_to < self.date_acceptance:
                return 0
            date_from = self.date_acceptance

        self_uat_set = self.unitavailabletime_set.filter(
            date_changed__range=[date_from, date_to]
        ).order_by('date_changed')
        self_uate_set = self.unitavailabletimeedit_set.filter(
            date__range=[date_from, date_to]
        ).order_by('date')

        # add latest uat where available
        latest_uat = self.unitavailabletime_set.filter(date_changed__lte=date_from).order_by("-date_changed")[:1]
        self_uat_set = self_uat_set | latest_uat

        potential_time = 0

        uate_list = {str(uate.date): uate.hours for uate in self_uate_set}

        val_list = self_uat_set.values(
            'date_changed', 'hours_sunday', 'hours_monday', 'hours_tuesday',
            'hours_wednesday', 'hours_thursday', 'hours_friday',
            'hours_saturday',
        )

        val_list_len = len(val_list)
        for i in range(val_list_len):
            next_date = val_list[i + 1]['date_changed'] - timedelta(days=1) if i < val_list_len - 1 else date_to
            this_date = date_from if val_list[i]['date_changed'] < date_from else val_list[i]['date_changed']

            days_nums = weekday_count(this_date, next_date, uate_list)

            for day in days_nums:
                potential_time += days_nums[day] * val_list[i]['hours_' + day].total_seconds()

        for uate in uate_list:
            potential_time += uate_list[uate].total_seconds()

        return potential_time / 3600

    def save(self, *args, **kwargs):
        if self.number in ("", None):
            next_available = Unit.objects.all().aggregate(max_num=Max("number") + 1)['max_num'] or 1
            self.number = next_available
        super().save(*args, **kwargs)

    def get_available_times_list(self):
        return [uat.to_dict() for uat in self.unitavailabletime_set.all()]


class UnitAvailableTimeEdit(models.Model):
    """
    A one off change to unit available time (holiday's, extended hours for a single day, etc)
    """
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)

    name = models.CharField(max_length=64, help_text=_l('A quick name or reason for the change'), blank=True, null=True)
    date = models.DateField(help_text=_l('Date of available time change'))
    hours = models.DurationField(help_text=_l('New duration of availability'))

    class Meta:
        ordering = ['-date']
        get_latest_by = 'date'
        unique_together = [('unit', 'date')]
        default_permissions = ()
        verbose_name = _l("unit available time edit")
        verbose_name_plural = _l('unit available time edits')

    def __str__(self):
        return '%s (%s)' % (self.name, fmt_date(self.date))


class UnitAvailableTime(models.Model):

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)

    date_changed = models.DateField(blank=True, help_text=_l('Date the units available time changed or will change'))
    hours_sunday = models.DurationField(help_text=_l('Duration of available time on Sundays'))
    hours_monday = models.DurationField(help_text=_l('Duration of available time on Mondays'))
    hours_tuesday = models.DurationField(help_text=_l('Duration of available time on Tuesdays'))
    hours_wednesday = models.DurationField(help_text=_l('Duration of available time on Wednesdays'))
    hours_thursday = models.DurationField(help_text=_l('Duration of available time on Thursdays'))
    hours_friday = models.DurationField(help_text=_l('Duration of available time on Fridays'))
    hours_saturday = models.DurationField(help_text=_l('Duration of available time on Saturdays'))

    class Meta:
        ordering = ['-date_changed']
        default_permissions = ('change',)
        get_latest_by = 'date_changed'
        unique_together = [('unit', 'date_changed')]
        verbose_name = _l("unit available time")
        verbose_name_plural = _l('unit available times')

    def __str__(self):
        return 'Available time schedule change'

    def to_dict(self):
        return {
            'date_changed': '{:02d}-{:02d}-{}'.format(self.date_changed.day, self.date_changed.month, self.date_changed.year),
            'hours_sunday': self.hours_sunday,
            'hours_monday': self.hours_monday,
            'hours_tuesday': self.hours_tuesday,
            'hours_wednesday': self.hours_wednesday,
            'hours_thursday': self.hours_thursday,
            'hours_friday': self.hours_friday,
            'hours_saturday': self.hours_saturday,
        }

    @staticmethod
    def available_times_on_unit_acceptance(unit_id):
        unit = Unit.objects.get(pk=unit_id)
        try:
            uat = UnitAvailableTime.objects.get(unit=unit, date_changed=unit.date_acceptance)
        except models.ObjectDoesNotExist:
            kwargs = {'unit': unit, 'date_changed': unit.date_acceptance}
            for d in settings.DEFAULT_AVAILABLE_TIMES:
                kwargs[d] = settings.DEFAULT_AVAILABLE_TIMES[d]
            uat = UnitAvailableTime(**kwargs)

        return uat


def get_unit_info(unit_ids=None, active_only=True):
    units = Unit.objects.all()
    if active_only:
        units = units.filter(active=True)
    if unit_ids:
        units = units.filter(pk__in=unit_ids)

    units = units.prefetch_related(
        "modalities",
        "treatment_techniques",
    ).order_by(
        "id",
        "modalities",
        "treatment_techniques",
    ).values_list(
        "id",
        "modalities",
        "treatment_techniques",
    )

    unit_info = defaultdict(lambda: {'treatment_techniques': set(), 'modalities': set()})

    for unit, modality, technique in units:
        if modality is not None:
            unit_info[unit]['modalities'].add(modality)
        if technique is not None:
            unit_info[unit]['treatment_techniques'].add(technique)

    return unit_info
