from django.contrib.contenttypes.models import ContentType
from rest_framework import viewsets

from qatrack.api.contenttypes.serializers import ContentTypeSerializer


class ContentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer
