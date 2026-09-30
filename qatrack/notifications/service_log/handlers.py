import logging

from django.conf import settings
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from qatrack.qa.signals import loaded_from_fixture
from qatrack.qatrack_core.email import send_email_to_users
from qatrack.service_log import models

logger = logging.getLogger('qatrack')


@receiver(post_save, sender=models.ServiceLog)
def on_serviceevent_saved(sender, instance, created, **kwargs):

    if loaded_from_fixture(kwargs):
        # `loaddata` saves with raw=True, and raw saves still fire post_save.
        # Without this guard the handler reaches through
        # `service_log.service_event` - a database lookup - and then tries to
        # *send email*, once per ServiceLog row in the fixture.
        #
        # It made `loaddata service_log` impossible against a real database: the
        # lookup raises ServiceEvent.DoesNotExist and the load aborts, naming
        # neither this handler nor notifications. `qatrack.service_log.signals`
        # has guarded its own receiver this way since it was written; this one
        # was missed.
        return

    service_log = instance
    recipients = get_notification_recipients(service_log.service_event, service_log.log_type)

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


def get_notification_recipients(service_event, log_type):

    from qatrack.notifications.service_log import models

    unit = service_event.unit_service_area.unit

    subs = models.ServiceEventNotice.objects.filter(
        Q(units=None) | Q(units__units=unit)
    ).select_related("recipients")  # yapf: disable

    subs = subs.filter(notification_type__in=[log_type, models.ServiceEventNotice.UPDATED_OR_CREATED])

    recipients = set()
    for sub in subs:
        recipients |= sub.recipients.recipient_emails()

    return recipients
