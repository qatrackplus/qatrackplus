from rest_framework import serializers

from qatrack.parts import models


class SupplierSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Supplier
        fields = "__all__"


class StorageSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Storage
        fields = "__all__"


class PartCategorySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.PartCategory
        fields = "__all__"


class PartSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Part
        fields = "__all__"


class PartStorageCollectionSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.PartStorageCollection
        fields = "__all__"


class PartSupplierCollectionSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.PartSupplierCollection
        fields = "__all__"


class PartUsedSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.PartUsed
        fields = "__all__"
