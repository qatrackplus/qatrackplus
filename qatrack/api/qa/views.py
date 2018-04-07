from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone
from rest_framework import status, parsers
from rest_framework import viewsets
from rest_framework import views
from rest_framework.response import Response

from qatrack.api.viewsets import CreateListRetrieveViewSet
from qatrack.api.qa import serializers
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


class TestListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestList.objects.all()
    serializer_class = serializers.TestListSerializer


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


class TestListInstanceViewSet(MultiSerializerMixin, viewsets.ModelViewSet):
    queryset = models.TestListInstance.objects.prefetch_related("attachment_set").all()
    serializer_class = serializers.TestListInstanceSerializer
    action_serializers = {
        'create': serializers.TestListInstanceCreator,
        'partial_update': serializers.TestListInstanceCreator,
    }
    http_method_names = ['get', 'post', 'patch']

    def create(self, request, *args, **kwargs):
        data = dict(request.data.items())
        serializer = self.get_serializer(data=data)
        serializer.user = request.user
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        # TODO : things to test
        #   - sublists
        #   - composite tests
        #   - file uploads / processing
        #   - attachments
        utc = serializer.validated_data['unit_test_collection']
        day = serializer.validated_data.get('day', 0)
        day, tl = utc.get_list(day=day)

        extra = {
            'created_by': self.request.user,
            'modified_by': self.request.user,
            'modified': timezone.now(),
            'due_date': utc.due_date,
            'test_list': tl,
            'site': get_current_site(self.request),
            'day': day,
        }
        serializer.save(**extra)

    def partial_update(self, request, *args, **kwargs):
        import ipdb; ipdb.set_trace()  # yapf: disable  # noqa
        return super(TestListInstanceViewSet, self).partial_update(request, *args, **kwargs)


class TestListCycleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestListCycle.objects.all()
    serializer_class = serializers.TestListCycleSerializer


class TestListCycleMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TestListCycleMembership.objects.all()
    serializer_class = serializers.TestListCycleMembershipSerializer
