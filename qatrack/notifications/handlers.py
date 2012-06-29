from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import signals
from django.dispatch import receiver
from django.template import Context
from django.template.loader import get_template

from qatrack import settings
from qatrack.qa.models import TestListInstance

from models import NotificationSubscriptions

#----------------------------------------------------------------------
@receiver(signals.post_save, sender=TestListInstance)
def email_on_testlist_save(*args,**kwargs):
    """TestListInstance was completed.  Send email notification if applicable"""

    if not email_enabled():
        return

    test_list_instance = kwargs["instance"]

    failing = failing_tests_to_report(test_list_instance)
    tolerance = tolerance_tests_to_report(test_list_instance)

    if not (failing or tolerance):
        return

    recipients = get_notification_recipient_emails()
    from_address = getattr(settings,"EMAIL_NOTIFICATION_SENDER", "QATrack+")
    subject = getattr(settings,"EMAIL_NOTIFICATION_SUBJECT","QATrack+ Notification")
    template = getattr(settings,"EMAIL_NOTIFICATION_TEMPLATE","notification_email.txt")

    body = get_template(template).render(
        Context({
            "failing_tests":failing,
            "tolerance_tests":tolerance,
            "test_list_instance":test_list_instance,
        })
    )

    send_mail(subject,body,from_address,recipients)

#----------------------------------------------------------------------
def email_enabled():
    """check if email notifications enabled"""
    return settings.EMAIL_ON_FAILING_TESTS or settings.EMAIL_ON_TOLERANCE_TESTS

#----------------------------------------------------------------------
def failing_tests_to_report(test_list_instance):
    """return failing tests to be reported for this test_list_instance"""
    if settings.EMAIL_ON_FAILING_TESTS:
        return test_list_instance.failing_tests()

#----------------------------------------------------------------------
def tolerance_tests_to_report(test_list_instance):
    """return tolerance tests to be reported for this test_list_instance"""
    if settings.EMAIL_ON_TOLERANCE_TESTS:
        return test_list_instance.tolerance_tests()

#----------------------------------------------------------------------
def get_notification_recipient_emails():
    users = User.objects.filter(groups__groupprofile__email_notifications=True)
    return users.values_list("email",flat=True)

