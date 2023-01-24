from django.db.models import Q
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework_filters import backends

from qatrack.api.service_log import filters, serializers
from qatrack.qatrack_core.dates import format_datetime
from qatrack.service_log import models


class ServiceAreaViewSet(viewsets.ModelViewSet):
    queryset = models.ServiceArea.objects.prefetch_related("units")
    serializer_class = serializers.ServiceAreaSerializer
    filterset_class = filters.ServiceAreaFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class UnitServiceAreaViewSet(viewsets.ModelViewSet):
    queryset = models.UnitServiceArea.objects.all()
    serializer_class = serializers.UnitServiceAreaSerializer
    filterset_class = filters.UnitServiceAreaFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ServiceTypeViewSet(viewsets.ModelViewSet):
    queryset = models.ServiceType.objects.all()
    serializer_class = serializers.ServiceTypeSerializer
    filterset_class = filters.ServiceTypeFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ServiceEventStatusViewSet(viewsets.ModelViewSet):
    queryset = models.ServiceEventStatus.objects.all()
    serializer_class = serializers.ServiceEventStatusSerializer
    filterset_class = filters.ServiceEventStatusFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ServiceEventViewSet(viewsets.ModelViewSet):
    queryset = models.ServiceEvent.objects.prefetch_related("service_event_related").all()
    serializer_class = serializers.ServiceEventSerializer
    filterset_class = filters.ServiceEventFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ThirdPartyViewSet(viewsets.ModelViewSet):
    queryset = models.ThirdParty.objects.all()
    serializer_class = serializers.ThirdPartySerializer
    filterset_class = filters.ThirdPartyFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class HoursViewSet(viewsets.ModelViewSet):
    queryset = models.Hours.objects.all()
    serializer_class = serializers.HoursSerializer
    filterset_class = filters.HoursFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ReturnToServiceQAViewSet(viewsets.ModelViewSet):
    queryset = models.ReturnToServiceQA.objects.all()
    serializer_class = serializers.ReturnToServiceQASerializer
    filterset_class = filters.ReturnToServiceQAFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class GroupLinkerViewSet(viewsets.ModelViewSet):
    queryset = models.GroupLinker.objects.all()
    serializer_class = serializers.GroupLinkerSerializer
    filterset_class = filters.GroupLinkerFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class GroupLinkerInstanceViewSet(viewsets.ModelViewSet):
    queryset = models.GroupLinkerInstance.objects.all()
    serializer_class = serializers.GroupLinkerInstanceSerializer
    filterset_class = filters.GroupLinkerInstanceFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


def service_event_searcher(request):
    q = request.GET.get('q')
    serviceevent = models.ServiceEvent.objects.filter(Q(id__icontains=q))[0:50]
    return JsonResponse({
        'items': [{
            'id': se.id,
            'display': '{} - Created on {}'.format(se.service_status.name, format_datetime(se.datetime_service))
        } for se in serviceevent],
        'name':
            'display'
    })
