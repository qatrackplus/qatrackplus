from django.contrib.auth.models import Group, Permission, User
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
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


class UserViewSet(MultiSerializerMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    """
    queryset = User.objects.prefetch_related("groups").order_by('username')
    serializer_class = UserSerializer
    action_serializers = {
        'list': UserListSerializer,
    }
    filterset_class = filters.UserFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )
    ordering_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "is_staff",
        "is_active",
        "is_superuser",
    )
    ordering = ("username",)


class GroupViewSet(MultiSerializerMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed and their permissions updated.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    action_serializers = {
        'list': GroupListSerializer,
    }
    filterset_class = filters.GroupFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )

    def update(self, request, *args, **kwargs):

        if not self.request.user.has_perm("auth.change_group"):
            return Response(status=status.HTTP_403_FORBIDDEN)

        elif self.request.data.get('type') in ('users', None):
            return super(GroupViewSet, self).update(request, *args, **kwargs)

        obj = self.get_object()

        try:
            app_label, codename = self.request.data['perm'].split(".")
            perm = Permission.objects.get(codename=codename, content_type__app_label=app_label)
        except Permission.DoesNotExist:
            resp = {'status': 'error', 'reason': "permission '%s' not found"}
            return Response(resp, status=status.HTTP_400_BAD_REQUEST)

        if self.request.data['active'] == "true":
            obj.permissions.add(perm)
            action = 'added'
        else:
            obj.permissions.remove(perm)
            action = 'removed'
        obj.save()
        resp = {'status': 'ok', 'permission': self.request.data['perm'], 'action': action}
        return Response(resp, status=status.HTTP_200_OK)


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows groups to be viewed.
    """
    queryset = Permission.objects.all().order_by('name')
    serializer_class = PermissionSerializer
    filterset_class = filters.PermissionFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )
