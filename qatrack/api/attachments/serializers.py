from rest_framework import serializers

from qatrack.attachments import models


class AttachmentSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Attachment
        fields = (
            'url',
            'attachment',
            'label',
            'comment',
            'test',
            'testlist',
            'testlistcycle',
            'testinstance',
            'testlistinstance',
            'created',
            'created_by',
        )
