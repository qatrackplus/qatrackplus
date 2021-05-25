import logging

from django.conf import settings
from django.utils import timezone
from django_q.models import Schedule

from qatrack.notifications.models import FaultsReviewNotice
from qatrack.qatrack_core.email import send_email_to_users
from qatrack.qatrack_core.tasks import run_periodic_scheduler, schedule, delete_schedule

logger = logging.getLogger('django-q')


def run_faults_review_notices():

    run_periodic_scheduler(
        FaultsReviewNotice,
        "run_faults_review_notices",
        schedule_faultsreview_notice,
        time_field="time",
        recurrence_field="recurrences",
    )


def schedule_faultsreview_notice(notice, send_time):

    logger.info("Scheduling notification %s for %s" % (notice.pk, send_time))
    name = "Send notification %d %s" % (notice.pk, send_time.isoformat())

    schedule(
        "qatrack.notifications.faults_review.tasks.send_faultsreview_notice",
        notice.id,
        name,
        name=name,
        schedule_type=Schedule.ONCE,
        repeats=1,
        next_run=send_time,
        task_name=name,
    )


def send_faultsreview_notice(*args, **kwargs):

    notice_id = args[0]
    task_name = kwargs.get("task_name", "")
    notice = FaultsReviewNotice.objects.filter(id=notice_id).first()

    if notice:

        if not notice.send_required():
            logger.info(
                "Send of FaultsReviewNotice %s requested, but no Faults to notify about" % notice_id
            )
            return

        recipients = notice.recipients.recipient_emails()
        if not recipients:
            logger.info("Send of FaultsReviewNotice %s requested, but no recipients" % notice_id)
            return
    else:
        logger.info(
            "Send of FaultsReviewNotice %s requested, but no such FaultsReviewNotice exists" % notice_id
        )
        return

    try:
        send_email_to_users(
            recipients,
            "faults_review/email.html",
            context={'notice': notice},
            subject_template="faults_review/subject.txt",
            text_template="faults_review/email.txt",
        )
        logger.info("Sent FaultsReviewNotice %s at %s" % (notice_id, timezone.now()))
        try:
            delete_schedule(task_name)
        except:  # noqa: E722  # pragma: nocover
            logger.exception("Unable to delete Schedule.name = %s after successful send" % task_name)
    except:  # noqa: E722  # pragma: nocover
        logger.exception(
            "Error sending email for FaultsReviewNotice %s at %s." % (notice_id, timezone.now())
        )

        fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        if not fail_silently:
            raise
    finally:
        notice.last_sent = timezone.now()
        notice.save()
