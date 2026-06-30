from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from qatrack.faults.models import Fault, FaultReviewInstance


@receiver(post_save, sender=Fault, dispatch_uid="faults_update_faults_cache_post_save")
@receiver(post_delete, sender=Fault, dispatch_uid="faults_update_faults_cache_post_delete")
@receiver(post_save, sender=FaultReviewInstance, dispatch_uid="faults_update_faults_cache_review_post_save")
@receiver(post_delete, sender=FaultReviewInstance, dispatch_uid="faults_update_faults_cache_review_post_delete")
def update_faults_cache(sender, **kwargs):
    """When a fault is changed invalidate the default and review count"""
    cache.delete(settings.CACHE_UNREVIEWED_FAULT_COUNT)
