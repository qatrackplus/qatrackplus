import rest_framework_filters as filters

from qatrack.units import models


class VendorFilter(filters.FilterSet):

    class Meta:
        model = models.UnitType
        fields = {
            "name": "__all__",
        }


class UnitClassFilter(filters.FilterSet):

    class Meta:
        model = models.UnitClass
        fields = {
            "name": "__all__",
        }


class SiteFilter(filters.FilterSet):

    class Meta:
        model = models.Site
        fields = {
            "name": "__all__",
        }


class UnitTypeFilter(filters.FilterSet):

    vendor = filters.RelatedFilter(VendorFilter, name='vendor', queryset=models.Vendor.objects.all())
    unit_class = filters.RelatedFilter(UnitClassFilter, name='unit_class', queryset=models.UnitClass.objects.all())

    class Meta:
        model = models.UnitType
        fields = {
            "name": "__all__",
            "model": "__all__",
        }


class ModalityFilter(filters.FilterSet):

    class Meta:
        model = models.Modality
        fields = {
            "name": "__all__",
        }


class UnitFilter(filters.FilterSet):

    type = filters.RelatedFilter(UnitTypeFilter, name='type', queryset=models.UnitType.objects.all())
    site = filters.RelatedFilter(SiteFilter, name='site', queryset=models.Site.objects.all())

    class Meta:
        model = models.Unit
        fields = {
            "number": '__all__',
            "name": '__all__',
            "serial_number": '__all__',
            "location": '__all__',
            "install_date": '__all__',
            "date_acceptance": '__all__',
            "active": '__all__',
        }


class UnitAvailableTimeFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, name="unit", queryset=models.Unit.objects.all())

    class Meta:
        model = models.UnitAvailableTimeEdit
        fields = {
            "name": "__all__",
            "date": "__all__",
            "hours": "__all__",
        }


class UnitAvailableTimeEditFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, name="unit", queryset=models.Unit.objects.all())

    class Meta:
        model = models.UnitAvailableTime
        fields = {
            "date_changed": "__all__",
            "hours_monday": "__all__",
            "hours_tuesday": "__all__",
            "hours_wednesday": "__all__",
            "hours_thursday": "__all__",
            "hours_friday": "__all__",
            "hours_saturday": "__all__",
            "hours_sunday": "__all__",
        }
