from rest_framework import serializers

from qatrack.faults import models


class FaultSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Fault
        fields = [
            "unit",
            "modality",
            "treatment_technique",
            "fault_type",
            "occurred",
        ]


class FaultTypeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.FaultType
        fields = "__all__"
