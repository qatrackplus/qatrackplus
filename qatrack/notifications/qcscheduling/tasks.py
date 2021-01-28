import logging

from django.conf import settings
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

from qatrack.notifications.models import QCSchedulingNotice
from qatrack.qatrack_core.email import send_email_to_users
from qatrack.qatrack_core.tasks import run_periodic_scheduler

logger = logging.getLogger('django-q')


def run_scheduling_notices():

    run_periodic_scheduler(
        QCSchedulingNotice,
        "run_scheduling_notices",
        schedule_scheduling_notice,
        time_field="time",
        recurrence_field="recurrences",
    )


def schedule_scheduling_notice(notice, send_time):

    logger.info("Scheduling notification %s for %s" % (notice.pk, send_time))
    name = "Send notification %d %s" % (notice.pk, send_time.isoformat())

    schedule(
        "qatrack.notifications.qcscheduling.tasks.send_scheduling_notice",
        notice.id,
        name,
        name=name,
        schedule_type=Schedule.ONCE,
        repeats=1,
        next_run=send_time,
        task_name=name,
    )


def send_scheduling_notice(notice_id, task_name=""):

    notice = QCSchedulingNotice.objects.filter(id=notice_id).first()

    if notice:

        if not notice.send_required():
            logger.info("Send of QCReviewNotice %s requested, but no QC to notify about" % notice_id)
            return

        recipients = notice.recipients.recipient_emails()
        if not recipients:
            logger.info("Send of QCSchedulingNotice %s requested, but no recipients" % notice_id)
            return
    else:
        logger.info("Send of QCSchedulingNotice %s requested, but no such QCSchedulingNotice exists" % notice_id)
        return

    try:
        send_email_to_users(
            recipients,
            "qcscheduling/email.html",
            context={'notice': notice},
            subject_template="qcscheduling/subject.txt",
            text_template="qcscheduling/email.txt",
        )
        logger.info("Sent QCSchedulingNotice %s at %s" % (notice_id, timezone.now()))
        try:
            Schedule.objects.get(name=task_name).delete()
        except:  # noqa: E722  # pragma: nocover
            logger.exception("Unable to delete Schedule.name = %s after successful send" % task_name)
    except:  # noqa: E722  # pragma: nocover
        logger.exception(
            "Error sending email for QCSchedulingNotice %s at %s." % (notice_id, timezone.now())
        )

        fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        if not fail_silently:
            raise
    finally:
        notice.last_sent = timezone.now()
        notice.save()
