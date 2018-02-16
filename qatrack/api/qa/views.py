from rest_framework import viewsets

from qatrack.api.qa import serializers
from qatrack.api.serializers import MultiSerializerMixin
from qatrack.qa import models


class FrequencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Frequency.objects.all()
    serializer_class = serializers.FrequencySerializer


class TestInstanceStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestInstanceStatus.objects.all()
    serializer_class = serializers.TestInstanceStatusSerializer


class AutoReviewRuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.AutoReviewRule.objects.all()
    serializer_class = serializers.AutoReviewRuleSerializer


class ReferenceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Reference.objects.all()
    serializer_class = serializers.ReferenceSerializer


class ToleranceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Tolerance.objects.all()
    serializer_class = serializers.ToleranceSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer


class TestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Test.objects.all()
    serializer_class = serializers.TestSerializer


class UnitTestInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitTestInfo.objects.all()
    serializer_class = serializers.UnitTestInfoSerializer


class TestListMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestListMembership.objects.all()
    serializer_class = serializers.TestListMembershipSerializer


class SublistViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Sublist.objects.all()
    serializer_class = serializers.SublistSerializer


class UnitTestCollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitTestCollection.objects.all()
    serializer_class = serializers.UnitTestCollectionSerializer


class TestInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestInstance.objects.all()
    serializer_class = serializers.TestInstanceSerializer


class TestListInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestListInstance.objects.all()
    serializer_class = serializers.TestListInstanceSerializer


class TestListCycleMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestListCycleMembership.objects.all()
    serializer_class = serializers.TestListCycleMembershipSerializer
