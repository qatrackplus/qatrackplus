from qatrack import settings

from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver


#----------------------------------------------------------------------
@receiver(post_save,sender=User)
def add_to_default_groups(sender,instance,created,**kwargs):
    """
    if any default groups are defined in settings the user will
    be added to them.
    """

    if created:
        group_names = getattr(settings,"DEFAULT_GROUP_NAMES",[])

        for group_name in group_names:

            group,_ = Group.objects.get_or_create(name=group_name)
            instance.groups.add(group)
            instance.save()

