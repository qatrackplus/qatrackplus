from rest_framework import serializers

from django_comments.models import Comment


class CommentSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Comment
        fields = (
            'url',
            'user',
            'submit_date',
            'comment',
        )
