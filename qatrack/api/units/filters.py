import rest_framework_filters as filters

from qatrack.api.filters import MaxDateFilter, MinDateFilter
from qatrack.units import models


class VendorFilter(filters.FilterSet):

    class Meta:
        model = models.Vendor
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
        }


class UnitClassFilter(filters.FilterSet):

    class Meta:
        model = models.UnitClass
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
        }


class SiteFilter(filters.FilterSet):

    class Meta:
        model = models.Site
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
        }


class UnitTypeFilter(filters.FilterSet):

    vendor = filters.RelatedFilter(VendorFilter, field_name='vendor', queryset=models.Vendor.objects.all())
    unit_class = filters.RelatedFilter(
        UnitClassFilter,
        field_name='unit_class',
        queryset=models.UnitClass.objects.all(),
    )

    class Meta:
        model = models.UnitType
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "model": ['exact', 'icontains', 'contains', 'in'],
        }


class ModalityFilter(filters.FilterSet):

    class Meta:
        model = models.Modality
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
        }


class UnitFilter(filters.FilterSet):

    type = filters.RelatedFilter(UnitTypeFilter, field_name='type', queryset=models.UnitType.objects.all())
    site = filters.RelatedFilter(SiteFilter, field_name='site', queryset=models.Site.objects.all())
    date_acceptance_min = MinDateFilter(field_name="date_acceptance")
    date_acceptance_max = MaxDateFilter(field_name="date_acceptance")
    install_date_min = MinDateFilter(field_name="install_date")
    install_date_max = MaxDateFilter(field_name="install_date")
    active = filters.BooleanFilter()

    class Meta:
        model = models.Unit
        fields = {
            "number": ['exact', 'in'],
            "name": ['exact', 'icontains', 'contains', 'in'],
            "serial_number": ['exact', 'icontains', 'contains', 'in'],
            "location": ['exact', 'icontains', 'contains', 'in'],
            "install_date": ['exact'],
            "date_acceptance": ['exact'],
        }


class UnitAvailableTimeEditFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, field_name="unit", queryset=models.Unit.objects.all())
    date_min = MinDateFilter(field_name="date")
    date_max = MaxDateFilter(field_name="date")

    class Meta:
        model = models.UnitAvailableTimeEdit
        fields = {
            "name": ['exact', 'icontains', 'contains', 'in'],
            "date": ['exact'],
        }


class UnitAvailableTimeFilter(filters.FilterSet):

    unit = filters.RelatedFilter(UnitFilter, field_name="unit", queryset=models.Unit.objects.all())

    date_changed_min = MinDateFilter(field_name="date_changed")
    date_changed_max = MaxDateFilter(field_name="date_changed")

    class Meta:
        model = models.UnitAvailableTime
        fields = {
            "date_changed": ['exact'],
        }
