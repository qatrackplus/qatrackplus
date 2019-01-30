from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework_filters import backends

from qatrack.api.serializers import MultiSerializerMixin
from qatrack.api.units import filters, serializers
from qatrack.units import models


class UnitViewSet(MultiSerializerMixin, viewsets.ReadOnlyModelViewSet):
    queryset = models.Unit.objects.all().order_by('number')
    serializer_class = serializers.UnitSerializer
    action_serializers = {
        'list': serializers.UnitListSerializer,
    }
    filterset_class = filters.UnitFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class VendorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Vendor.objects.all().order_by('name')
    serializer_class = serializers.VendorSerializer
    filterset_class = filters.VendorFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class UnitClassViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitClass.objects.all().order_by('name')
    serializer_class = serializers.UnitClassSerializer
    filterset_class = filters.UnitClassFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class UnitTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitType.objects.all().order_by('name')
    serializer_class = serializers.UnitClassSerializer
    filterset_class = filters.UnitFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ModalityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Modality.objects.all().order_by('name')
    serializer_class = serializers.ModalitySerializer
    filterset_class = filters.ModalityFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Site.objects.all().order_by('name')
    serializer_class = serializers.SiteSerializer
    filterset_class = filters.SiteFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class UnitAvailableTimeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitAvailableTime.objects.all().order_by('unit__number', "-date_changed")
    serializer_class = serializers.UnitAvailableTimeSerializer
    filterset_class = filters.UnitAvailableTimeFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class UnitAvailableTimeEditViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitAvailableTimeEdit.objects.all().order_by('unit__number', "-date")
    serializer_class = serializers.UnitAvailableTimeEditSerializer
    filterset_class = filters.UnitAvailableTimeEditFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)
