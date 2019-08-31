import logging

from django.conf import settings
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from qatrack.qatrack_core.email import send_email_to_users
from qatrack.service_log import models

logger = logging.getLogger('qatrack')


@receiver(post_save, sender=models.ServiceLog)
def on_serviceevent_saved(sender, instance, created, **kwargs):

    service_log = instance
    recipients = get_notification_recipients(service_log.service_event)

    if not recipients:
        return

    context = {
        'service_event': service_log.service_event,
        'service_log': service_log,
    }

    try:
        send_email_to_users(
            recipients,
            "service_log/email.html",
            context=context,
            subject_template="service_log/subject.txt",
            text_template="service_log/email.txt",
        )
        logger.info(
            "Sent Service Event Notice for service event %d at %s" % (service_log.service_event_id, timezone.now())
        )
    except:  # noqa: E722  # pragma: nocover
        logger.exception(
            "Error sending Service Event Notice for service event %d at %s." %
            (service_log.service_event_id, timezone.now())
        )

        fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        if not fail_silently:
            raise


def get_notification_recipients(service_event):

    from qatrack.notifications.service_log import models

    unit = service_event.unit_service_area.unit

    subs = models.ServiceEventNotice.objects.filter(
        (Q(units=None) | Q(units__units=unit))
    ).select_related("recipients")  # yapf: disable

    recipients = set()
    for sub in subs:
        recipients |= sub.recipients.recipient_emails()

    return recipients
