from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import Signal, receiver
from django.utils import timezone
from django_comments.models import Comment
from django_comments.signals import comment_was_posted

from qatrack.service_log import models


@receiver(post_delete, sender=models.ServiceEvent)
def clear_se_needing_review_count(*args, **kwargs):
    import ipdb; ipdb.set_trace()  # yapf: disable  # noqa
    cache.delete(settings.CACHE_SE_NEEDING_REVIEW_COUNT)

