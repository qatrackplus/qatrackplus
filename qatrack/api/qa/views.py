from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone
from rest_framework import status, views, viewsets
from rest_framework.response import Response

from qatrack.api.qa import serializers, filters
from qatrack.api.serializers import MultiSerializerMixin
from qatrack.qa import models
from qatrack.qa.views import perform


class CompositeCalculation(perform.CompositeCalculation, views.APIView):
    permission_classes = []


class Upload(perform.CompositeCalculation, views.APIView):
    permission_classes = []


class FrequencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Frequency.objects.all()
    serializer_class = serializers.FrequencySerializer
    filter_class = filters.FrequencyFilter


class TestInstanceStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestInstanceStatus.objects.all()
    serializer_class = serializers.TestInstanceStatusSerializer
    filter_class = filters.TestInstanceStatusFilter


class AutoReviewRuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.AutoReviewRule.objects.all()
    serializer_class = serializers.AutoReviewRuleSerializer
    filter_class = filters.AutoReviewRuleFilter


class ReferenceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Reference.objects.all()
    serializer_class = serializers.ReferenceSerializer
    filter_class = filters.ReferenceFilter


class ToleranceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Tolerance.objects.all()
    serializer_class = serializers.ToleranceSerializer
    filter_class = filters.ToleranceFilter


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    filter_class = filters.CategoryFilter


class TestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Test.objects.all()
    serializer_class = serializers.TestSerializer
    filter_class = filters.TestFilter


class TestListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestList.objects.all()
    serializer_class = serializers.TestListSerializer
    filter_class = filters.TestListFilter


class UnitTestInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitTestInfo.objects.all()
    serializer_class = serializers.UnitTestInfoSerializer
    filter_class = filters.UnitTestInfoFilter


class TestListMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestListMembership.objects.all()
    serializer_class = serializers.TestListMembershipSerializer
    filter_class = filters.TestListMembershipFilter


class SublistViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Sublist.objects.all()
    serializer_class = serializers.SublistSerializer
    filter_class = filters.SublistFilter


class UnitTestCollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.UnitTestCollection.objects.all()
    serializer_class = serializers.UnitTestCollectionSerializer
    filter_class = filters.UnitTestCollectionFilter


class TestInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestInstance.objects.all()
    serializer_class = serializers.TestInstanceSerializer
    filter_class = filters.TestInstanceFilter


class TestListInstanceViewSet(MultiSerializerMixin, viewsets.ModelViewSet):
    queryset = models.TestListInstance.objects.prefetch_related("attachment_set").all()
    serializer_class = serializers.TestListInstanceSerializer
    filter_class = filters.TestListInstanceFilter
    action_serializers = {
        'create': serializers.TestListInstanceCreator,
        'partial_update': serializers.TestListInstanceCreator,
    }
    http_method_names = ['get', 'post', 'patch']

    def get_serializer(self, *args, **kwargs):
        ser = super(TestListInstanceViewSet, self).get_serializer(*args, **kwargs)
        ser.site = get_current_site(self.request)
        ser.user = self.request.user
        return ser

    def create(self, request, *args, **kwargs):
        data = dict(request.data.items())
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        utc = serializer.validated_data['unit_test_collection']
        day = serializer.validated_data.get('day', 0)
        day, tl = utc.get_list(day=day)

        extra = {
            'created_by': self.request.user,
            'modified_by': self.request.user,
            'modified': timezone.now(),
            'due_date': utc.due_date,
            'test_list': tl,
            'day': day,
        }
        serializer.save(**extra)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        comment = serializer.comment

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            serializer.comment = comment
            serializer.user = request.user

        return Response(serializer.data)


class TestListCycleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestListCycle.objects.all()
    serializer_class = serializers.TestListCycleSerializer
    filter_class = filters.TestListCycleFilter


class TestListCycleMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestListCycleMembership.objects.all()
    serializer_class = serializers.TestListCycleMembershipSerializer
    filter_class = filters.TestListCycleMembershipFilter
