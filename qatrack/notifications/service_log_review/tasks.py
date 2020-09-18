import logging

from django.conf import settings
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

from qatrack.notifications.models import ServiceEventReviewNotice
from qatrack.qatrack_core.email import send_email_to_users
from qatrack.qatrack_core.tasks import run_periodic_scheduler

logger = logging.getLogger('qatrack')


def run_service_event_review_notices():

    run_periodic_scheduler(
        ServiceEventReviewNotice,
        "run_service_event_review_notices",
        schedule_serviceeventreview_notice,
        time_field="time",
        recurrence_field="recurrences",
    )


def schedule_serviceeventreview_notice(notice, send_time):

    logger.info("Scheduling notification %s for %s" % (notice.pk, send_time))
    name = "Send notification %d %s" % (notice.pk, send_time.isoformat())

    schedule(
        "qatrack.notifications.service_log_review.tasks.send_serviceeventreview_notice",
        notice.id,
        name,
        name=name,
        schedule_type=Schedule.ONCE,
        repeats=1,
        next_run=send_time,
        task_name=name,
    )


def send_serviceeventreview_notice(notice_id, task_name=""):

    notice = ServiceEventReviewNotice.objects.filter(id=notice_id).first()

    if notice:

        if not notice.send_required():
            logger.info(
                "Send of ServiceEventReviewNotice %s requested, but no ServiceEvent to notify about" % notice_id
            )
            return

        recipients = notice.recipients.recipient_emails()
        if not recipients:
            logger.info("Send of ServiceEventReviewNotice %s requested, but no recipients" % notice_id)
            return
    else:
        logger.info(
            "Send of ServiceEventReviewNotice %s requested, but no such ServiceEventReviewNotice exists" % notice_id
        )
        return

    try:
        send_email_to_users(
            recipients,
            "service_log_review/email.html",
            context={'notice': notice},
            subject_template="service_log_review/subject.txt",
            text_template="service_log_review/email.txt",
        )
        logger.info("Sent ServiceEventReviewNotice %s at %s" % (notice_id, timezone.now()))
        try:
            Schedule.objects.get(name=task_name).delete()
        except:  # noqa: E722  # pragma: nocover
            logger.exception("Unable to delete Schedule.name = %s after successful send" % task_name)
    except:  # noqa: E722  # pragma: nocover
        logger.exception(
            "Error sending email for ServiceEventReviewNotice %s at %s." % (notice_id, timezone.now())
        )

        fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        if not fail_silently:
            raise
    finally:
        notice.last_sent = timezone.now()
        notice.save()
