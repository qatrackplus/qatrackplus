from rest_framework import serializers

from qatrack.service_log import models


class ServiceAreaSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ServiceArea
        fields = "__all__"


class UnitServiceAreaSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.UnitServiceArea
        fields = "__all__"


class ServiceTypeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ServiceType
        fields = "__all__"


class ServiceEventStatusSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ServiceEventStatus
        fields = "__all__"


class ServiceEventSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ServiceEvent
        fields = "__all__"


class ThirdPartySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ThirdParty
        fields = "__all__"


class HoursSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Hours
        fields = "__all__"


class ReturnToServiceQASerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ReturnToServiceQA
        fields = "__all__"


class GroupLinkerSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.GroupLinker
        fields = "__all__"


class GroupLinkerInstanceSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.GroupLinkerInstance
        fields = "__all__"
