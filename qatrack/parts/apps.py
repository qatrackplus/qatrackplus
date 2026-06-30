from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _l


class PartsConfig(AppConfig):
    name = 'qatrack.parts'
    verbose_name = _l("Parts")

    def ready(self):
        import qatrack.parts.signals  # noqa 