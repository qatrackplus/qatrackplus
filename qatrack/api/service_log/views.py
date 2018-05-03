from rest_framework import viewsets

from qatrack.api.service_log import filters, serializers
from qatrack.service_log import models


class ServiceAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceArea.objects.all()
    serializer_class = serializers.ServiceAreaSerializer
    filter_class = filters.ServiceAreaFilter


class UnitServiceAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitServiceArea.objects.all()
    serializer_class = serializers.UnitServiceAreaSerializer
    filter_class = filters.UnitServiceAreaFilter


class ServiceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceType.objects.all()
    serializer_class = serializers.ServiceTypeSerializer
    filter_class = filters.ServiceTypeFilter


class ServiceEventStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceEventStatus.objects.all()
    serializer_class = serializers.ServiceEventStatusSerializer
    filter_class = filters.ServiceEventStatusFilter


class ServiceEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceEvent.objects.all()
    serializer_class = serializers.ServiceEventSerializer
    filter_class = filters.ServiceEventFilter


class ThirdPartyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ThirdParty.objects.all()
    serializer_class = serializers.ThirdPartySerializer
    filter_class = filters.ThirdPartyFilter


class HoursViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Hours.objects.all()
    serializer_class = serializers.HoursSerializer
    filter_class = filters.HoursFilter


class ReturnToServiceQAViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ReturnToServiceQA.objects.all()
    serializer_class = serializers.ReturnToServiceQASerializer
    filter_class = filters.ReturnToServiceQAFilter


class GroupLinkerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.GroupLinker.objects.all()
    serializer_class = serializers.GroupLinkerSerializer
    filter_class = filters.GroupLinkerFilter


class GroupLinkerInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.GroupLinkerInstance.objects.all()
    serializer_class = serializers.GroupLinkerInstanceSerializer
    filter_class = filters.GroupLinkerInstanceFilter
