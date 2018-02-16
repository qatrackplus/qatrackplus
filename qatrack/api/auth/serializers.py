from django.contrib.auth.models import Group, User
from rest_framework import serializers


class UserListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = (
            'url',
            'username',
            'email',
            'groups',
        )


class UserSerializer(serializers.HyperlinkedModelSerializer):

    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'url',
            'username',
            'first_name',
            'last_name',
            'email',
            'permissions',
            'groups',
        )

    def get_permissions(self, obj):
        return sorted(obj.get_all_permissions()) if obj else []


class GroupListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Group
        fields = ('url', 'name')


class GroupSerializer(serializers.HyperlinkedModelSerializer):

    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ('url', 'name', "permissions", "user_set")

    def get_permissions(self, obj):
        return [
            '.'.join(x) for x in obj.permissions.select_related(
                "content_type",
            ).order_by(
                'content_type__app_label',
                'codename',
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        ] if obj else []
