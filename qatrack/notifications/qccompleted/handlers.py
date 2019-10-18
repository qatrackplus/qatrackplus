from collections import defaultdict
import logging

from django.conf import settings
from django.db.models import Q
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

from qatrack.qa.models import TestListInstance
from qatrack.qa.signals import testlist_complete
from qatrack.qatrack_core.email import send_email_to_users

logger = logging.getLogger('qatrack')


@receiver(testlist_complete)
def email_on_testlist_save(*args, **kwargs):
    """TestListInstance was completed.  Send email notification if applicable"""

    test_list_instance = kwargs["instance"]

    failing = test_list_instance.failing_tests().select_related(
        "tolerance",
        "reference",
        "unit_test_info",
        "unit_test_info__test",
    ).order_by("order", "created")
    tolerance = test_list_instance.tolerance_tests().select_related(
        "tolerance",
        "reference",
        "unit_test_info",
        "unit_test_info__test",
    ).order_by("order", "created")

    recipients = get_notification_recipients(test_list_instance)
    comp_recipients, tol_recipients, act_recipients = recipients

    if not (failing or tolerance or comp_recipients):
        return

    recipients = comp_recipients
    if tolerance:
        recipients |= tol_recipients
    if failing:
        recipients |= act_recipients

    context = {
        "failing_tests": failing,
        "tolerance_tests": tolerance,
        "test_list_instance": test_list_instance,
        "notice_type": "completed",
    }

    template = getattr(settings, "EMAIL_NOTIFICATION_TEMPLATE", "notification_email.html")
    subject_template = getattr(settings, "EMAIL_NOTIFICATION_SUBJECT_TEMPLATE", "notification_email_subject.txt")

    send_email_to_users(recipients, template, context, subject_template=subject_template)


def get_notification_recipients(test_list_instance):

    from qatrack.notifications import models

    unit = test_list_instance.unit_test_collection.unit
    test_list = test_list_instance.test_list

    subs = models.QCCompletedNotice.objects.filter(
        (Q(units=None) | Q(units__units=unit)) &
        (Q(test_lists=None) | Q(test_lists__test_lists=test_list))
    ).exclude(
        notification_type=models.QCCompletedNotice.FOLLOW_UP,
    ).select_related("recipients")  # yapf: disable

    recipients = defaultdict(set)
    for sub in subs:
        recipients[sub.notification_type] |= sub.recipients.recipient_emails()

    return (
        recipients[models.QCCompletedNotice.COMPLETED],
        recipients[models.QCCompletedNotice.TOLERANCE],
        recipients[models.QCCompletedNotice.ACTION],
    )


@receiver(testlist_complete)
def follow_up_emails(signal, sender, instance, created, **kwargs):
    """When a test list is completed, create Schedule objects any follow up
    notifications that need to be scheduled"""

    from qatrack.notifications.models import QCCompletedNotice

    notices = QCCompletedNotice.objects.filter(
        notification_type=QCCompletedNotice.FOLLOW_UP,
        follow_up_days__isnull=False,
        test_lists__test_lists__id=instance.test_list.id,
    ).filter(Q(units__units=None) | Q(units__units=instance.unit_test_collection.unit))

    if not notices or instance.in_progress:
        return

    if not created:
        # clear any existing scheduled notices before rescheduling
        Schedule.objects.filter(name__contains="follow-up-for-tli-%d-" % instance.pk).delete()

    for notice in notices:
        follow_up = instance.work_completed + timezone.timedelta(days=notice.follow_up_days)
        name = "follow-up-for-tli-%d-notice-%d" % (instance.pk, notice.pk)
        schedule(
            "qatrack.notifications.qccompleted.tasks.send_follow_up_email",
            name=name,
            schedule_type=Schedule.ONCE,
            next_run=follow_up,
            test_list_instance_id=instance.pk,
            notification_id=notice.id,
        )


@receiver(post_delete, sender=TestListInstance)
def clean_up_follow_up_emails(*args, **kwargs):
    """Test list instance was deleted.  Remove any scheduled follow up emails for it"""
    Schedule.objects.filter(name__contains="follow-up-for-tli-%d-" % kwargs['instance'].pk).delete()
