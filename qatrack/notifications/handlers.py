from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.dispatch import receiver
from django.template import Context
from django.template.loader import get_template

from qatrack.qa.signals import testlist_complete


import models


#----------------------------------------------------------------------
@receiver(testlist_complete)
def email_on_testlist_save(*args, **kwargs):
    """TestListInstance was completed.  Send email notification if applicable"""

    test_list_instance = kwargs["instance"]

    failing = failing_tests_to_report(test_list_instance)
    tolerance = tolerance_tests_to_report(test_list_instance)

    if not (failing or tolerance):
        return

    tol_recipients, act_recipients = get_notification_recipients()

    recipients = tol_recipients
    if failing:
        recipients |= act_recipients

    recipient_emails = recipients.distinct().values_list("email", flat=True)

    from_address = getattr(settings, "EMAIL_NOTIFICATION_SENDER", "QATrack+")
    subject = getattr(settings, "EMAIL_NOTIFICATION_SUBJECT", "QATrack+ Notification")
    template = getattr(settings, "EMAIL_NOTIFICATION_TEMPLATE", "notification_email.txt")
    user = getattr(settings, "EMAIL_NOTIFICATION_USER", None)
    pwd = getattr(settings, "EMAIL_NOTIFICATION_PWD", None)
    fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)

    body = get_template(template).render(
        Context({
            "subject": subject,
            "failing_tests": failing,
            "tolerance_tests": tolerance,
            "test_list_instance": test_list_instance,
        })
    )

    send_mail(
        subject, body, from_address, recipient_emails,
        auth_user=user, auth_password=pwd,
        fail_silently=fail_silently
    )


#----------------------------------------------------------------------
def failing_tests_to_report(test_list_instance):
    """return failing tests to be reported for this test_list_instance"""
    return test_list_instance.failing_tests()

#----------------------------------------------------------------------


def tolerance_tests_to_report(test_list_instance):
    """return tolerance tests to be reported for this test_list_instance"""
    return test_list_instance.tolerance_tests()

#----------------------------------------------------------------------


def get_notification_recipients():
    tolerance_users = User.objects.filter(groups__notificationsubscription__warning_level__lte=models.TOLERANCE).distinct()
    action_users = User.objects.filter(groups__notificationsubscription__warning_level__lte=models.ACTION).distinct()

    return tolerance_users, action_users
