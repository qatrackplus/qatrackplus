from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
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


class ActiveDirectoryGroupMap(models.Model):

    ad_group = models.CharField(
        _l("Active Directory Group"),
        max_length=256,
        unique=True,
        help_text=_l(
            "Enter the name of the group from your Active Directory Server. "
            "Leave blank to add all users to the selected QATrack+ groups"
        ),
        blank=True,
    )

    groups = models.ManyToManyField(
        Group,
        verbose_name=_l("QATrack+ Groups"),
        help_text=_l(
            "Select the QATrack+ groups you want this user added to when they belong to the Active Directory Group"
        ),
        blank=True,
    )

    account_qualifier = models.BooleanField(
        verbose_name=_l("Account Qualifying Group"),
        help_text=_l(
            "Add this Active Directory Group to the set of Active Directory Groups of which a user must "
            "belong to at least one in order to log into QATrack+. (If there are no qualifying groups "
            "then all authenticated users may log into QATrack+.)"
        ),
        default=False,
    )

    class Meta:
        verbose_name = _l("Active Directory Group to QATrack+ Group Map")
        verbose_name_plural = _l("Active Directory Group to QATrack+ Group Maps")

    @classmethod
    def group_map(cls):
        group_map = {g.ad_group: list(g.groups.all()) for g in cls.objects.prefetch_related("groups").all()}
        return group_map

    @classmethod
    def qualified_ad_group_names(cls):
        return list(cls.objects.filter(account_qualifier=True).order_by("ad_group").values_list("ad_group", flat=True))
