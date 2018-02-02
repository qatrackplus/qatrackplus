from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from qatrack.qa.signals import testlist_complete


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
    subject_template = getattr(settings, "EMAIL_NOTIFICATION_SUBJECT_TEMPLATE", "notification_email_subject.txt")
    template = getattr(settings, "EMAIL_NOTIFICATION_TEMPLATE", "notification_email.html")
    user = getattr(settings, "EMAIL_NOTIFICATION_USER", None)
    pwd = getattr(settings, "EMAIL_NOTIFICATION_PWD", None)
    fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)

    current_site = Site.objects.get_current()

    context = {
        "failing_tests": failing,
        "tolerance_tests": tolerance,
        "test_list_instance": test_list_instance,
        "domain": current_site.domain,
    }

    if subject_template is not None:
        subject = render_to_string(subject_template, context).strip()

    html_body = render_to_string(template, context)
    text_body = strip_tags(html_body)

    send_mail(
        subject,
        text_body,
        from_address,
        recipient_emails,
        html_message=html_body,
        auth_user=user,
        auth_password=pwd,
        fail_silently=fail_silently,
    )


def failing_tests_to_report(test_list_instance):
    """return failing tests to be reported for this test_list_instance"""
    return test_list_instance.failing_tests()


def tolerance_tests_to_report(test_list_instance):
    """return tolerance tests to be reported for this test_list_instance"""
    return test_list_instance.tolerance_tests()


def get_notification_recipients():

    from qatrack.notifications import models

    users = User.objects.filter(is_active=True)

    tolerance_users = users.filter(
        groups__notificationsubscription__warning_level__lte=models.TOLERANCE
    ).distinct()
    action_users = users.filter(
        groups__notificationsubscription__warning_level__lte=models.ACTION
    ).distinct()

    return tolerance_users, action_users
