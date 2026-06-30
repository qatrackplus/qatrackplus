from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from qatrack.parts.models import PartStorageCollection, PartUsed


@receiver(pre_delete, sender=PartUsed, dispatch_uid="parts_update_part_storage_quantity")
def update_part_storage_quantity(sender, instance, **kwargs):
    # Return parts used to storage:
    instance.add_back_to_storage()


@receiver(post_delete, sender=PartStorageCollection, dispatch_uid="parts_update_part_quantity")
def update_part_quantity(sender, instance, **kwargs):
    part = instance.part
    part.set_quantity_current()
