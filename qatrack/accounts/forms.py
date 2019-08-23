from django.contrib.auth.views import PasswordChangeForm, SetPasswordForm as SetPasswordFormBase
from registration.forms import RegistrationForm


class RegisterForm(RegistrationForm):
    pass


class ChangePasswordForm(PasswordChangeForm):
    pass


class SetPasswordForm(SetPasswordFormBase):
    pass
