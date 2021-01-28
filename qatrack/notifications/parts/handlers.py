import logging

from django.conf import settings
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone

from qatrack.parts import models
from qatrack.qatrack_core.email import send_email_to_users

logger = logging.getLogger('qatrack')


@receiver(post_save, sender=models.Part)
def on_part_saved(sender, instance, created, **kwargs):

    update_fields = kwargs['update_fields']
    quantity_did_not_change = update_fields is None or 'quantity_current' not in update_fields
    if created or quantity_did_not_change:
        return

    part = instance

    if part.quantity_current >= part.quantity_min:
        return

    recipients = get_notification_recipients(part)

    if not recipients:
        return

    context = {
        'part': part,
    }

    try:
        send_email_to_users(
            recipients,
            "parts/email.html",
            context=context,
            subject_template="parts/subject.txt",
            text_template="parts/email.txt",
        )
        logger.info(
            "Sent Parts Notice for part %d at %s" % (part.id, timezone.now())
        )
    except:  # noqa: E722  # pragma: nocover
        logger.exception(
            "Error sending Part Notice for part %d at %s." %
            (part.id, timezone.now())
        )

        fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        if not fail_silently:
            raise


def get_notification_recipients(part):

    from qatrack.notifications.parts import models

    subs = models.PartNotice.objects.filter(
        (Q(part_categories=None) | Q(part_categories__part_categories=part.part_category))
    ).select_related("recipients")  # yapf: disable

    recipients = set()
    for sub in subs:
        recipients |= sub.recipients.recipient_emails()

    return recipients
