from rest_framework import serializers

from qatrack.qa import models


class FrequencySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Frequency
        fields = "__all__"


class TestInstanceStatusSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestInstanceStatus
        fields = "__all__"


class AutoReviewRuleSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.AutoReviewRule
        fields = "__all__"


class ReferenceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Reference
        fields = "__all__"


class ToleranceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Tolerance
        fields = "__all__"


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Category
        fields = "__all__"


class TestSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Test
        fields = "__all__"


class TestListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.TestList
        fields = "__all__"


class UnitTestInfoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.UnitTestInfo
        fields = "__all__"


class TestListMembershipSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestListMembership
        fields = "__all__"


class SublistSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Sublist
        fields = "__all__"


class UnitTestCollectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.UnitTestCollection
        fields = "__all__"


class TestInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestInstance
        fields = "__all__"


class TestListInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.TestListInstance
        fields = "__all__"


class TestListCycleSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.TestListCycle
        fields = "__all__"


class TestListCycleMembershipSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.TestListCycleMembership
        fields = "__all__"
