from django_comments.models import Comment
from rest_framework import viewsets

from qatrack.api.comments import serializers


class CommentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Comment.objects.all().order_by('-submit_date')
    serializer_class = serializers.CommentSerializer
