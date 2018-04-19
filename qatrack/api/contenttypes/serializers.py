from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers


class ContentTypeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ContentType
        fields = '__all__'
