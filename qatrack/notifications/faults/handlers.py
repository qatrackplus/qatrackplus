import logging

from django.conf import settings
from django.db.models import Q
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone

from qatrack.faults import models
from qatrack.qatrack_core.email import send_email_to_users

logger = logging.getLogger('qatrack')


@receiver(m2m_changed, sender=models.Fault.fault_types.through)
def on_fault_created(sender, instance, action, **kwargs):

    if action != "post_add":
        # don't send when edited
        return

    fault = instance
    recipients = get_notification_recipients(fault)

    if not recipients:
        return

    context = {'fault': fault}

    try:
        send_email_to_users(
            recipients,
            "faults/email.html",
            context=context,
            subject_template="faults/subject.txt",
            text_template="faults/email.txt",
        )
        logger.info(
            "Sent Fault Notice for fault id %d at %s" % (fault.id, timezone.now())
        )
    except:  # noqa: E722  # pragma: nocover
        logger.exception(
            "Error sending Fault Logged Notice for fault id %d at %s." %
            (fault.id, timezone.now())
        )

        fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        if not fail_silently:
            raise


def get_notification_recipients(fault):

    from qatrack.notifications.faults import models

    unit = fault.unit

    subs = models.FaultNotice.objects.filter(
        (Q(units=None) | Q(units__units=unit))
    ).select_related("recipients")  # yapf: disable

    recipients = set()
    for sub in subs:
        recipients |= sub.recipients.recipient_emails()

    return recipients
