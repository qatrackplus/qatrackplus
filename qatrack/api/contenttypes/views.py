from django.contrib.contenttypes.models import ContentType
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
import rest_framework_filters as filters
from rest_framework_filters import backends

from qatrack.api.contenttypes.serializers import ContentTypeSerializer


class ContentTypeFilter(filters.FilterSet):

    class Meta:
        model = ContentType
        fields = {
            "app_label": "__all__",
            "model": "__all__",
        }


class ContentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer
    filter_class = ContentTypeFilter
    filter_backends = (backends.DjangoFilterBackend, OrderingFilter,)
