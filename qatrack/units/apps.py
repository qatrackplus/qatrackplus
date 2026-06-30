from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _l


class UnitsConfig(AppConfig):
    name = 'qatrack.units'
    verbose_name = _l("Units") 