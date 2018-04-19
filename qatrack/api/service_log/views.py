from rest_framework import viewsets

from qatrack.api.service_log import serializers
from qatrack.service_log import models


class ServiceAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceArea.objects.all()
    serializer_class = serializers.ServiceAreaSerializer


class UnitServiceAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitServiceArea.objects.all()
    serializer_class = serializers.UnitServiceAreaSerializer


class ServiceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceType.objects.all()
    serializer_class = serializers.ServiceTypeSerializer


class ServiceEventStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceEventStatus.objects.all()
    serializer_class = serializers.ServiceEventStatusSerializer


class ServiceEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ServiceEvent.objects.all()
    serializer_class = serializers.ServiceEventSerializer


class ThirdPartyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ThirdParty.objects.all()
    serializer_class = serializers.ThirdPartySerializer


class HoursViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Hours.objects.all()
    serializer_class = serializers.HoursSerializer


class ReturnToServiceQAViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.ReturnToServiceQA.objects.all()
    serializer_class = serializers.ReturnToServiceQASerializer


class GroupLinkerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.GroupLinker.objects.all()
    serializer_class = serializers.GroupLinkerSerializer


class GroupLinkerInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.GroupLinkerInstance.objects.all()
    serializer_class = serializers.GroupLinkerInstanceSerializer
