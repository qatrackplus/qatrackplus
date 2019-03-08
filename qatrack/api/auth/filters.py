from django.contrib.auth.models import Group, Permission, User
import rest_framework_filters as filters

from qatrack.api.contenttypes.views import ContentType, ContentTypeFilter
from qatrack.api.filters import MaxDateFilter, MinDateFilter


class UserFilter(filters.FilterSet):

    date_joined_min = MinDateFilter(name="date_joined")
    date_joined_max = MaxDateFilter(name="date_joined")

    class Meta:
        model = User
        fields = {
            "username": ["icontains", "in"],
            "first_name": ["icontains", "in"],
            "last_name": ["icontains", "in"],
            "email": ["icontains", "in"],
            "is_staff": ["exact"],
            "is_active": ["exact"],
            "date_joined": ["exact"],
        }


class PermissionFilter(filters.FilterSet):

    content_type = filters.RelatedFilter(ContentTypeFilter, field_name="content_type", queryset=ContentType.objects.all())

    class Meta:
        model = Permission
        fields = {
            "name": ["icontains", "in"],
            "codename": ["icontains", "in"],
        }


class GroupFilter(filters.FilterSet):

    permissions = filters.RelatedFilter(PermissionFilter, field_name="permissions", queryset=Permission.objects.all())

    class Meta:
        model = Group
        fields = {
            "name": ["icontains", "in"],
        }
