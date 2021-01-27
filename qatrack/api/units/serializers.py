from rest_framework import serializers

from qatrack.units import models


class UnitListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Unit
        fields = (
            'url',
            'name',
            'number',
            'site',
        )


class UnitSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Unit
        fields = "__all__"


class VendorSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Vendor
        fields = "__all__"


class UnitClassSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.UnitClass
        fields = "__all__"


class UnitTypeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.UnitType
        fields = "__all__"


class ModalitySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Modality
        fields = "__all__"


class TreatmentTechniqueSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.TreatmentTechnique
        fields = "__all__"


class SiteSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Site
        fields = "__all__"


class UnitAvailableTimeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.UnitAvailableTime
        fields = "__all__"


class UnitAvailableTimeEditSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.UnitAvailableTimeEdit
        fields = "__all__"
