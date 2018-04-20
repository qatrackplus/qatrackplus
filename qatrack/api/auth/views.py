from django.contrib.auth.models import Group, Permission, User
from rest_framework import viewsets
import rest_framework_filters as filters

from qatrack.api.auth.serializers import (GroupListSerializer, GroupSerializer, UserListSerializer, UserSerializer)
from qatrack.api.serializers import MultiSerializerMixin
from qatrack.api.contenttypes.views import ContentType, ContentTypeFilter


class UserFilter(filters.FilterSet):

    class Meta:
        model = User
        fields = {
            "username": "__all__",
            "first_name": "__all__",
            "last_name": "__all__",
            "email": "__all__",
            "is_staff": "__all__",
            "is_active": "__all__",
            "date_joined": "__all__",
        }


class UserViewSet(viewsets.ReadOnlyModelViewSet, MultiSerializerMixin):
    """
    API endpoint that allows users to be viewed.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    action_serializers = {
        'list': UserListSerializer,
    }
    filter_class = UserFilter


class PermissionFilter(filters.FilterSet):

    content_type = filters.RelatedFilter(ContentTypeFilter, name="content_type", queryset=ContentType.objects.all())

    class Meta:
        model = Permission
        fields = {
            "name": "__all__",
            "codename": "__all__",
        }


class GroupFilter(filters.FilterSet):

    permissions = filters.RelatedFilter(PermissionFilter, name="permissions", queryset=Permission.objects.all())

    class Meta:
        model = Group
        fields = {
            "name": "__all__",
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
