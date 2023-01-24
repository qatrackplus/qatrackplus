from rest_framework import serializers

from qatrack.faults import models


class FaultSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Fault
        fields = [
            "unit",
            "modality",
            "fault_types",
            "occurred",
        ]


class FaultTypeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.FaultType
        fields = "__all__"
