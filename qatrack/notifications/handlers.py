import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db.models import Q
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import pynliner

from qatrack.qa.signals import testlist_complete

logger = logging.getLogger('qatrack')


@receiver(testlist_complete)
def email_on_testlist_save(*args, **kwargs):
    """TestListInstance was completed.  Send email notification if applicable"""

    test_list_instance = kwargs["instance"]

    failing = failing_tests_to_report(test_list_instance)
    tolerance = tolerance_tests_to_report(test_list_instance)

    recipients = get_notification_recipients(test_list_instance)
    comp_recipients, tol_recipients, act_recipients = recipients

    if not (failing or tolerance or comp_recipients):
        return

    recipients = comp_recipients
    if tolerance:
        recipients |= tol_recipients
    if failing:
        recipients |= act_recipients

    recipient_emails = recipients.distinct().values_list("email", flat=True)
    if len(recipient_emails) == 0:
        return

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

    html_body = pynliner.fromString(render_to_string(template, context))
    text_body = strip_tags(html_body)

    try:
        send_mail(
            subject,
            text_body,
            from_address,
            recipient_emails,
            html_message=html_body,
            auth_user=user,
            auth_password=pwd,
            fail_silently=False,
        )
    except:  # noqa: E722
        logger.exception("Error sending email.")
        if not fail_silently:
            raise


def failing_tests_to_report(test_list_instance):
    """return failing tests to be reported for this test_list_instance"""
    return test_list_instance.failing_tests()


def tolerance_tests_to_report(test_list_instance):
    """return tolerance tests to be reported for this test_list_instance"""
    return test_list_instance.tolerance_tests()


def get_notification_recipients(test_list_instance):

    from qatrack.notifications import models

    unit = test_list_instance.unit_test_collection.unit
    test_list = test_list_instance.test_list

    users = User.objects.filter(is_active=True).exclude(email='')

    subs = models.NotificationSubscription.objects.filter(
        (Q(units=None) | Q(units=unit)) &
        (Q(test_lists=None) | Q(test_lists=test_list))
    )  # yapf: disable

    completed_subs = subs.filter(warning_level__lte=models.COMPLETED)
    tolerance_subs = subs.filter(warning_level__lte=models.TOLERANCE)
    action_subs = subs.filter(warning_level__lte=models.ACTION)

    completed_users = users.filter(
        Q(groups__notificationsubscriptions__in=completed_subs) |
        Q(notificationsubscriptions__in=completed_subs)
    ).distinct()
    tolerance_users = users.filter(
        Q(groups__notificationsubscriptions__in=tolerance_subs) |
        Q(notificationsubscriptions__in=tolerance_subs)
    ).distinct()
    action_users = users.filter(
        Q(groups__notificationsubscriptions__in=action_subs) |
        Q(notificationsubscriptions__in=action_subs)
    ).distinct()

    return completed_users, tolerance_users, action_users
