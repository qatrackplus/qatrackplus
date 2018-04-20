from django.contrib.contenttypes.models import ContentType
from rest_framework import viewsets
import rest_framework_filters as filters

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
