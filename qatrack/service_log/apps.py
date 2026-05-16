from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _l


class ServiceLogAppConfig(AppConfig):
    name = "qatrack.service_log"
    verbose_name = _l("Service Log")
