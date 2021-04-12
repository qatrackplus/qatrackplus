from django.contrib.auth.views import PasswordChangeForm
from django.contrib.auth.views import SetPasswordForm as SetPasswordFormBase
from django_registration.forms import RegistrationForm


class RegisterForm(RegistrationForm):
    pass


class ChangePasswordForm(PasswordChangeForm):
    pass


class SetPasswordForm(SetPasswordFormBase):
    pass
