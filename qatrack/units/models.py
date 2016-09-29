from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _

from django.apps import apps


# ServiceArea = apps.get_app_config('service_log').get_model('ServiceArea')
# UnitServiceArea = apps.get_app_config('service_log').get_model('UnitServiceArea')

PHOTON = "photon"
ELECTRON = "electron"


class Vendor(models.Model):
    """ Vendor of Unit

    Stores information (just name for now) of unit vendor.
    """

    name = models.CharField(max_length=64, unique=True, help_text=_('Name of this vendor'))

    def __unicode__(self):
        """Display more descriptive name"""
        return "<Vendor(%s)>" % self.name


class UnitClass(models.Model):
    """ Class of unit

    Unit class, ie. linac, CT, MR, etc.
    """

    name = models.CharField(max_length=64, unique=True, help_text=_('Name of this unit class'))

    def __unicode__(self):
        """Display more descriptive name"""
        return "<UnitClass(%s)>" % self.name


class Site(models.Model):
    """ Site unit resides

    Allows for multiple site filtering (different campuses, buildings, hospitals, etc)
    """
    name = models.CharField(max_length=64, unique=True, help_text=_('Name of this site'))

    def __unicode__(self):
        return '<Site(%s)>' % self.name


class UnitType(models.Model):
    """Radiation Device Type

    Stores a device type for grouping individual :model:`unit`s together.
    For example, your Elekta Linacs might form one group, and your Tomo's
    another.

    TODO: improve model types
    """
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.PROTECT)
    unit_class = models.ForeignKey(UnitClass, null=True, blank=True, on_delete=models.PROTECT)

    name = models.CharField(max_length=50, help_text=_("Name for this unit type"))
    model = models.CharField(max_length=50, null=True, blank=True, help_text=_("Optional model name for this group"))

    class Meta:
        unique_together = [("name", "model")]

    def __unicode__(self):
        """Display more descriptive name"""
        return "<UnitType(%s,%s)>" % (self.name, self.model)


class Modality(models.Model):
    """Treatment modalities

    defines available treatment modalities for a given :model:`unit1`

    """

    name = models.CharField(
        _("Name"),
        max_length=255,
        help_text=_("Descriptive name for this modality"),
        unique=True
    )

    class Meta:
        verbose_name_plural = _("Modalities")

    def __unicode__(self):
        return self.name


class Unit(models.Model):
    """Radiation devices

    Stores a single radiation device (e.g. Linac, Tomo unit, Cyberkinfe etc.)

    """

    number = models.PositiveIntegerField(null=False, unique=True, help_text=_("A unique number for this unit"))
    name = models.CharField(max_length=256, help_text=_("The display name for this unit"))
    serial_number = models.CharField(max_length=256, null=True, blank=True, help_text=_("Optional serial number"))
    location = models.CharField(max_length=256, null=True, blank=True, help_text=_("Optional location information"))
    install_date = models.DateField(null=True, blank=True, help_text=_("Optional install date"))
    date_acceptance = models.DateField(null=True, blank=True, help_text=_('Optional date of acceptance'))
    active = models.BooleanField(default=True, help_text=_('Set to false if unit is no longer in use'))
    restricted = models.BooleanField(default=False, help_text=_('Set to false to restrict unit from operation'))

    type = models.ForeignKey(UnitType, on_delete=models.PROTECT)
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.PROTECT)

    modalities = models.ManyToManyField(Modality)

    # objects = UnitManager()

    class Meta:
        ordering = [settings.ORDER_UNITS_BY]

    def __unicode__(self):
        return self.name
