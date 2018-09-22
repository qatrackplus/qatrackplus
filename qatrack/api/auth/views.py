from django.contrib.auth.models import Group, Permission, User
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework_filters import backends

from qatrack.api.auth import filters
from qatrack.api.auth.serializers import (
    GroupListSerializer,
    GroupSerializer,
    PermissionSerializer,
    UserListSerializer,
    UserSerializer,
)
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
    filter_class = filters.UserFilter
    filter_backends = (backends.DjangoFilterBackend, OrderingFilter,)
    ordering_fields = ("username", "first_name", "last_name", "email", "is_staff", "is_active", "is_superuser",)
    ordering = ("username",)


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows groups to be viewed.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    action_serializers = {
        'list': GroupListSerializer,
    }
    filter_class = filters.GroupFilter
    filter_backends = (backends.DjangoFilterBackend, OrderingFilter,)


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows groups to be viewed.
    """
    queryset = Permission.objects.all().order_by('name')
    serializer_class = PermissionSerializer
    filter_class = filters.PermissionFilter
    filter_backends = (backends.DjangoFilterBackend, OrderingFilter,)
