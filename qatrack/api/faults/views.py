from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework_filters import backends

from qatrack.api.faults import filters, serializers
from qatrack.faults import models


class FaultViewSet(viewsets.ModelViewSet):
    queryset = models.Fault.objects.prefetch_related("fault_types").all()
    serializer_class = serializers.FaultSerializer
    filterset_class = filters.FaultFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )


class FaultTypeViewSet(viewsets.ModelViewSet):
    queryset = models.FaultType.objects.all()
    serializer_class = serializers.FaultTypeSerializer
    filterset_class = filters.FaultTypeFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )
