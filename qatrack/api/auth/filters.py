from django.contrib.auth.models import Group, Permission, User
import rest_framework_filters as filters

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


class PermissionFilter(filters.FilterSet):

    content_type = filters.RelatedFilter(ContentTypeFilter, field_name="content_type", queryset=ContentType.objects.all())

    class Meta:
        model = Permission
        fields = {
            "name": "__all__",
            "codename": "__all__",
        }


class GroupFilter(filters.FilterSet):

    permissions = filters.RelatedFilter(PermissionFilter, field_name="permissions", queryset=Permission.objects.all())

    class Meta:
        model = Group
        fields = {
            "name": "__all__",
        }
