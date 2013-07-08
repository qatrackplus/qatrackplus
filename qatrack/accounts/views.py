from django.views.generic.base import TemplateView
from qatrack.qa.models import PERMISSIONS

class AccountDetails(TemplateView):
    template_name="registration/account.html"

    def get_context_data(self, **kwargs):

        context = super(AccountDetails, self).get_context_data(**kwargs)
        all_perms = self.request.user.get_all_permissions()
        permissions = []
        for category, perms in PERMISSIONS:
            category_perms = []
            for perm, title, desc in perms:
               category_perms.append((perm in all_perms, title, desc))

            permissions.append((category,category_perms))

        context["permissions"] = permissions

        return context
