from rest_framework import viewsets

from qatrack.api.attachments import serializers
from qatrack.attachments import models


class AttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Attachment.objects.all().order_by('-created')
    serializer_class = serializers.AttachmentSerializer
