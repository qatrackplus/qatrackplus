import logging

from django.conf import settings

from qatrack.qa.models import TestListInstance
from qatrack.qatrack_core.email import send_email_to_users
from qatrack.qatrack_core.models import ScheduledDelivery

logger = logging.getLogger('django-q2')


def follow_up_delivery_name(test_list_instance, notice, follow_up):
    """Identifies one follow-up email: one notice, for one test list instance, due at one time.

    A notice can have several follow-ups due at the same moment, one for each
    test list instance, so unlike the other notices the due time alone doesn't
    identify the email.

    The handler that queues a follow-up adds the time it was queued. Editing a
    test list instance queues its follow-ups afresh, and one queued again after
    the first has gone out is a new email, not a second copy of the old one.
    """
    return "follow-up-for-tli-%d-notice-%d at %s" % (test_list_instance.pk, notice.pk, follow_up.isoformat())


def send_follow_up_email(test_list_instance_id=None, notification_id=None, delivery_name=""):
    """Task to do the actual sending of the follow up emails

    `delivery_name` (see follow_up_delivery_name) lets a second copy of the same
    scheduled task see that the email has already gone (#919). Follow-ups
    queued before it was added have none, and are sent unguarded as before.
    """

    from qatrack.notifications.models import QCCompletedNotice

    tli = TestListInstance.objects.filter(pk=test_list_instance_id).first()
    sub = QCCompletedNotice.objects.filter(id=notification_id).first()
    if not (tli and sub):
        return

    recipients = sub.recipients.recipient_emails()
    context = {
        'notice_type': "follow_up",
        'test_list_instance': tli,
    }
    template = getattr(settings, "EMAIL_NOTIFICATION_TEMPLATE", "notification_email.html")
    subject_template = getattr(settings, "EMAIL_NOTIFICATION_SUBJECT_TEMPLATE", "notification_email_subject.txt")

    claim = ScheduledDelivery.claim(sub, delivery_name, occurrence=delivery_name)
    if claim is None:
        logger.info("Follow up %s was already sent" % delivery_name)
        return

    sent = False
    try:
        sent = send_email_to_users(recipients, template, context, subject_template=subject_template)
    finally:
        claim.finish(sent)
