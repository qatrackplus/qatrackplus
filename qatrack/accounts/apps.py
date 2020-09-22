from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _l


class AccountsAppConfig(AppConfig):

    name = 'qatrack.accounts'
    verbose_name = _l("Authentication and Authorization Backend Settings")
