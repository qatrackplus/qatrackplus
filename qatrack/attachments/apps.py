from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _l


class AttachmentsConfig(AppConfig):
    name = 'qatrack.attachments'
    verbose_name = _l("Attachments")
