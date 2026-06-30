from django.db import models
from django.utils.translation import gettext_lazy as _l


class Contact(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=("ID"))
    """basic contact number"""
    name = models.CharField(max_length=256)
    number = models.CharField(max_length=256)
    description = models.TextField()

    class Meta:
        verbose_name = _l("Contact")
        verbose_name_plural = _l("Contacts")

    def __str__(self):
        return "%s : %s " % (self.name, self.number)
