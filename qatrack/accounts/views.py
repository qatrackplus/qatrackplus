import json

from django.contrib.auth import logout
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.views.generic.base import TemplateView

from qatrack.qa.models import PERMISSIONS


class AccountDetails(TemplateView):
    template_name = "accounts/account.html"

    def get_context_data(self, **kwargs):

        context = super(AccountDetails, self).get_context_data(**kwargs)
        all_perms = self.request.user.get_all_permissions()
        permissions = []
        for category, perms in PERMISSIONS:
            category_perms = []
            for perm, title, desc in perms:
                category_perms.append((perm in all_perms, title, desc))

            permissions.append((category, category_perms))

        context["permissions"] = permissions

        return context


class GroupsApp(PermissionRequiredMixin, TemplateView):

    template_name = "accounts/groups.html"
    permission_required = "auth.change_group"

    def get_context_data(self, **kwargs):
        context = super(GroupsApp, self).get_context_data(**kwargs)
        context["all_perms"] = json.dumps(PERMISSIONS)
        context["groups"] = Group.objects.all()
        return context


def logout_view(request):
    logout(request)
