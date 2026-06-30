from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _l


class ContactsConfig(AppConfig):
    name = 'qatrack.contacts'
    verbose_name = _l("Contacts") 