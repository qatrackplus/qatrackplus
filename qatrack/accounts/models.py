import uuid

from django.conf import settings
from django.db import models

from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import gettext_lazy as _l


@receiver(post_save, sender=User)
def add_to_default_groups(sender, instance, created, **kwargs):
    """
    if any default groups are defined in settings the user will
    be added to them.
    """

    if created:
        group_names = getattr(settings, "DEFAULT_GROUP_NAMES", [])

        for group_name in group_names:

            group, _ = Group.objects.get_or_create(name=group_name)
            instance.groups.add(group)
            instance.save()


class ActiveDirectoryGroupConversion(models.Model):

    ad_group = models.CharField(
        _l("Active Directory Group"),
        max_length=256,
        unique=True,
        help_text=_l("Enter the name of the group from your Active Directory Server"),
    )

    groups = models.ManyToManyField(
        Group,
        verbose_name=_l("QATrack+ Groups"),
        help_text=_l(
            "Select the QATrack+ groups you want this user added to when they belong to the Active Directory Group"
        ),
    )


class ADFSConfig(models.Model):

    server = models.CharField(
        _l("Server"),
        max_length=128,
        help_text=_l("URL of your ADFS server (e.g. adfs.yourhospital.com)"),
    )
    client_id = models.CharField(
        _l("Client ID"),
        max_length=64,
        help_text=_l(
            "ClientID of the ADFS Client configured on your ADFS Server. "
            "Leave blank to have a random UUID generated",
        ),
        default=lambda: str(uuid.uuid4),
        blank=True,
    )
    relying_party_id = models.CharField(
        _l("Relying Party ID"),
        max_length=128,
        help_text=_l("Typically you can set this to e.g. http://yourqatrackserver/"),
    )
    audience = models.CharField(
        _l("Audience"),
        max_length=128,
        help_text=_l("Typically you can set this to e.g. http://yourqatrackserver/"),
    )
    username_claim = models.CharField(
        _l("Username Claim"),
        max_length=64,
        help_text=_l("Name of the claim field that holds the users username. (default=winaccountname)"),
        default="winaccountname",
        blank=True,
    )
    group_claim = models.CharField(
        _l("Group Claim"),
        max_length=64,
        help_text=_l("Name of the claim field that holds the users AD Groups. (default=group)"),
        default="group",
        blank=True,
    )
    first_name_claim = models.CharField(
        _l("First Name Claim"),
        max_length=64,
        help_text=_l("Name of the claim field that holds the users first name. (default=given_name)"),
        default="given_name",
        blank=True,
    )

    last_name_claim = models.CharField(
        _l("Last Name Claim"),
        max_length=64,
        help_text=_l("Name of the claim field that holds the users surname. (default=family_name)"),
        default="family_name",
        blank=True,
    )

    class Meta:
        unique_together = [("server", "client_id")]
