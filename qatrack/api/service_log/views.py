from django.db.models import Q
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework_filters import backends

from qatrack.api.service_log import filters, serializers
from qatrack.service_log import models


class ServiceAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceArea.objects.all()
    serializer_class = serializers.ServiceAreaSerializer
    filterset_class = filters.ServiceAreaFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class UnitServiceAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitServiceArea.objects.all()
    serializer_class = serializers.UnitServiceAreaSerializer
    filterset_class = filters.UnitServiceAreaFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ServiceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceType.objects.all()
    serializer_class = serializers.ServiceTypeSerializer
    filterset_class = filters.ServiceTypeFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ServiceEventStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceEventStatus.objects.all()
    serializer_class = serializers.ServiceEventStatusSerializer
    filterset_class = filters.ServiceEventStatusFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ServiceEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceEvent.objects.all()
    serializer_class = serializers.ServiceEventSerializer
    filterset_class = filters.ServiceEventFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ThirdPartyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ThirdParty.objects.all()
    serializer_class = serializers.ThirdPartySerializer
    filterset_class = filters.ThirdPartyFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class HoursViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Hours.objects.all()
    serializer_class = serializers.HoursSerializer
    filterset_class = filters.HoursFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class ReturnToServiceQAViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ReturnToServiceQA.objects.all()
    serializer_class = serializers.ReturnToServiceQASerializer
    filterset_class = filters.ReturnToServiceQAFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class GroupLinkerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.GroupLinker.objects.all()
    serializer_class = serializers.GroupLinkerSerializer
    filterset_class = filters.GroupLinkerFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class GroupLinkerInstanceViewSet(viewsets.ReadOnlyModelViewSet):
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
            'display': '{} - Created on {}'.format(se.service_status.name, se.datetime_service.strftime('%b %d, %Y'))
        } for se in serviceevent],
        'name':
            'display'
    })
