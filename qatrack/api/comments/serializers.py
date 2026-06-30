from django_comments.models import Comment
from rest_framework import serializers


class CommentSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Comment
        fields = (
            'url',
            'user',
            'submit_date',
            'comment',
        )
