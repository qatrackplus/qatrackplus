from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _l


class FaultsConfig(AppConfig):
    name = 'qatrack.faults'
    verbose_name = _l("Faults")

    def ready(self):
        import qatrack.faults.signals  # noqa
