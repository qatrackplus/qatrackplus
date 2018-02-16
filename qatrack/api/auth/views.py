from django.contrib.auth.models import Group, User
from rest_framework import viewsets

from qatrack.api.auth.serializers import (GroupListSerializer, GroupSerializer, UserListSerializer, UserSerializer)
from qatrack.api.serializers import MultiSerializerMixin


class UserViewSet(viewsets.ReadOnlyModelViewSet, MultiSerializerMixin):
    """
    API endpoint that allows users to be viewed.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    action_serializers = {
        'list': UserListSerializer,
    }


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows groups to be viewed.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    action_serializers = {
        'list': GroupListSerializer,
    }
