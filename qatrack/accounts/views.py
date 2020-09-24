import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import (
    PasswordChangeView,
    PasswordResetConfirmView,
)
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView
from django_auth_adfs.views import OAuth2CallbackView
from registration.backends.simple.views import RegistrationView

from qatrack.accounts.forms import (
    ChangePasswordForm,
    RegisterForm,
    SetPasswordForm,
)
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


class RegisterView(RegistrationView):

    form_class = RegisterForm

    def register(self, form):
        super().register(form)
        domain = Site.objects.get_current().domain
        context = {
            'user': form.cleaned_data['username'],
            'login_link': "%s%s" % (domain, settings.LOGIN_URL),
        }

        text_content = get_template("registration/welcome_email.txt").render(context)
        html_content = get_template("registration/welcome_email.html").render(context)
        email = EmailMultiAlternatives(
            subject='Welcome to QATrack+',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[form.cleaned_data['email']],
            bcc=[settings.DEFAULT_FROM_EMAIL],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=not settings.DEBUG)


class ChangePasswordView(PasswordChangeView):

    form_class = ChangePasswordForm


class ResetPasswordConfirmView(PasswordResetConfirmView):

    form_class = SetPasswordForm


class GroupsApp(PermissionRequiredMixin, TemplateView):

    template_name = "accounts/groups.html"
    permission_required = "auth.change_group"

    def get_context_data(self, **kwargs):
        context = super(GroupsApp, self).get_context_data(**kwargs)
        context["all_perms"] = json.dumps(PERMISSIONS, cls=DjangoJSONEncoder)
        context["groups"] = Group.objects.all()
        return context


class QATrackOAuth2CallbackView(OAuth2CallbackView):

    def get(self, request):
        result = super().get(request)
        if result.status_code >= 400:
            if result.status_code == 400:
                msg = _("Login failed with error 400: No authorization code was provided")
            elif result.status_code == 401:
                msg = _("Login failed with error 401: Your account is not authorized to use QATrack+")
            elif result.status_code == 403:
                msg = _("Login failed with error 403: Your account is disabled")
            else:
                msg = _("Login Failed with error {status_code}: {phrase}").format(
                    status_code=result.status_code, phrase=result.reason_phrase
                )
            messages.error(request, msg)
            return redirect(settings.LOGIN_URL)
        return result
