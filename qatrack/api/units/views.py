from rest_framework import viewsets

from qatrack.api.serializers import MultiSerializerMixin
from qatrack.api.units import serializers, filters
from qatrack.units import models


class UnitViewSet(viewsets.ReadOnlyModelViewSet, MultiSerializerMixin):
    queryset = models.Unit.objects.all().order_by('number')
    serializer_class = serializers.UnitSerializer
    action_serializers = {
        'list': serializers.UnitListSerializer,
    }
    filter_class = filters.UnitFilter


class VendorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Vendor.objects.all().order_by('name')
    serializer_class = serializers.VendorSerializer
    filter_class = filters.VendorFilter


class UnitClassViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitClass.objects.all().order_by('name')
    serializer_class = serializers.UnitClassSerializer
    filter_class = filters.UnitClassFilter


class UnitTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitType.objects.all().order_by('name')
    serializer_class = serializers.UnitClassSerializer
    filter_class = filters.UnitFilter


class ModalityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Modality.objects.all().order_by('name')
    serializer_class = serializers.ModalitySerializer
    filter_class = filters.ModalityFilter


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Site.objects.all().order_by('name')
    serializer_class = serializers.SiteSerializer
    filter_class = filters.SiteFilter


class UnitAvailableTimeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitAvailableTime.objects.all().order_by('unit__number', "-date_changed")
    serializer_class = serializers.UnitAvailableTimeSerializer
    filter_class = filters.UnitAvailableTimeFilter


class UnitAvailableTimeEditViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitAvailableTimeEdit.objects.all().order_by('unit__number', "-date")
    serializer_class = serializers.UnitAvailableTimeEditSerializer
    filter_class = filters.UnitAvailableTimeEditFilter
