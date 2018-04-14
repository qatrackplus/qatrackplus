from rest_framework import viewsets
import rest_framework_filters as filters

from qatrack.api.serializers import MultiSerializerMixin
from qatrack.api.units import serializers
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
            "restricted": '__all__',
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


class UnitViewSet(viewsets.ReadOnlyModelViewSet, MultiSerializerMixin):
    queryset = models.Unit.objects.all().order_by('number')
    serializer_class = serializers.UnitSerializer
    action_serializers = {
        'list': serializers.UnitListSerializer,
    }
    filter_class = UnitFilter


class VendorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Vendor.objects.all().order_by('name')
    serializer_class = serializers.VendorSerializer
    filter_class = VendorFilter


class UnitClassViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitClass.objects.all().order_by('name')
    serializer_class = serializers.UnitClassSerializer
    filter_class = UnitClassFilter


class UnitTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitType.objects.all().order_by('name')
    serializer_class = serializers.UnitClassSerializer
    filter_class = UnitFilter


class ModalityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Modality.objects.all().order_by('name')
    serializer_class = serializers.ModalitySerializer
    filter_class = ModalityFilter


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Site.objects.all().order_by('name')
    serializer_class = serializers.SiteSerializer
    filter_class = SiteFilter


class UnitAvailableTimeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitAvailableTime.objects.all().order_by('unit__number', "-date_changed")
    serializer_class = serializers.UnitAvailableTimeSerializer
    filter_class = UnitAvailableTimeFilter


class UnitAvailableTimeEditViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitAvailableTimeEdit.objects.all().order_by('unit__number', "-date")
    serializer_class = serializers.UnitAvailableTimeEditSerializer
    filter_class = UnitAvailableTimeEditFilter
