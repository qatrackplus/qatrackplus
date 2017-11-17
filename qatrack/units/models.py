
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _

from django.apps import apps

# from qatrack.qa.models import Frequency


# ServiceArea = apps.get_app_config('service_log').get_model('ServiceArea')
# UnitServiceArea = apps.get_app_config('service_log').get_model('UnitServiceArea')

PHOTON = 'photon'
ELECTRON = 'electron'


class Vendor(models.Model):
    """ Vendor of Unit

    Stores information (just name for now) of unit vendor.
    """

    name = models.CharField(max_length=64, unique=True, help_text=_('Name of this vendor'))
    notes = models.TextField(max_length=255, blank=True, null=True, help_text=_('Additional notes about this vendor'))

    def __str__(self):
        """Display more descriptive name"""
        return self.name


class UnitClass(models.Model):
    """ Class of unit

    Unit class, ie. linac, CT, MR, etc.
    """

    name = models.CharField(max_length=64, unique=True, help_text=_('Name of this unit class'))

    def __str__(self):
        """Display more descriptive name"""
        return '<UnitClass(%s)>' % self.name


class Site(models.Model):
    """ Site unit resides

    Allows for multiple site filtering (different campuses, buildings, hospitals, etc)
    """
    name = models.CharField(max_length=64, unique=True, help_text=_('Name of this site'))

    def __str__(self):
        return self.name


class UnitType(models.Model):
    """Radiation Device Type

    Stores a device type for grouping individual :model:`unit`s together.
    For example, your Elekta Linacs might form one group, and your Tomo's
    another.

    TODO: improve model types
    """
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.PROTECT)
    unit_class = models.ForeignKey(UnitClass, null=True, blank=True, on_delete=models.PROTECT)

    name = models.CharField(max_length=50, help_text=_('Name for this unit type'))
    model = models.CharField(max_length=50, null=True, blank=True, help_text=_('Optional model name for this group'))

    class Meta:
        unique_together = [('name', 'model')]

    def __str__(self):
        """Display more descriptive name"""
        return '%s%s' % (self.name, ' - %s' % self.model if self.model else '')


class Modality(models.Model):
    """Treatment modalities

    defines available treatment modalities for a given :model:`unit1`

    """

    name = models.CharField(
        _('Name'),
        max_length=255,
        help_text=_('Descriptive name for this modality'),
        unique=True
    )

    class Meta:
        verbose_name_plural = _('Modalities')

    def __str__(self):
        return self.name


class Unit(models.Model):
    """Radiation devices
    Stores a single radiation device (e.g. Linac, Tomo unit, Cyberkinfe etc.)
    """
    type = models.ForeignKey(UnitType, on_delete=models.PROTECT)
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.PROTECT)

    number = models.PositiveIntegerField(null=False, unique=True, help_text=_('A unique number for this unit'))
    name = models.CharField(max_length=256, help_text=_('The display name for this unit'))
    serial_number = models.CharField(max_length=256, null=True, blank=True, help_text=_('Optional serial number'))
    location = models.CharField(max_length=256, null=True, blank=True, help_text=_('Optional location information'))
    install_date = models.DateField(null=True, blank=True, help_text=_('Optional install date'))
    date_acceptance = models.DateField(null=True, blank=True, help_text=_('Optional date of acceptance'))
    active = models.BooleanField(default=True, help_text=_('Set to false if unit is no longer in use'))
    restricted = models.BooleanField(default=False, help_text=_('Set to false to restrict unit from operation'))

    modalities = models.ManyToManyField(Modality)

    # objects = UnitManager()

    class Meta:
        ordering = [settings.ORDER_UNITS_BY]

    def __str__(self):
        return self.name


class UnitAvailableTimeEdit(models.Model):
    """
    A one off change to unit available time (holiday's, extended hours for a single day, etc)
    """
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)

    name = models.CharField(max_length=64, help_text=_('A quick name or reason for the change'))
    date = models.DateField(help_text=_('Date of available time change'))
    hours = models.DurationField(help_text=_('New duration of availability'))

    class Meta:
        ordering = ['-date']
        get_latest_by = 'date'
        unique_together = [('unit', 'date')]

    def __str__(self):
        return '%s (%s)' % (self.name, self.date.strftime('%b %d, %Y'))


class UnitAvailableTime(models.Model):

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)

    date_changed = models.DateField(help_text=_('Date the units available time changed or will change'))
    hours_monday = models.DurationField(help_text=_('Duration of available time on Mondays'))
    hours_tuesday = models.DurationField(help_text=_('Duration of available time on Tuesdays'))
    hours_wednesday = models.DurationField(help_text=_('Duration of available time on Wednesdays'))
    hours_thursday = models.DurationField(help_text=_('Duration of available time on Thursdays'))
    hours_friday = models.DurationField(help_text=_('Duration of available time on Fridays'))
    hours_saturday = models.DurationField(help_text=_('Duration of available time on Saturdays'))
    hours_sunday = models.DurationField(help_text=_('Duration of available time on Sundays'))

    class Meta:
        ordering = ['-date_changed']
        default_permissions = ('change',)
        get_latest_by = 'date_changed'
        unique_together = [('unit', 'date_changed')]

    def __str__(self):
        return 'Available time for %s' % self.unit.name
