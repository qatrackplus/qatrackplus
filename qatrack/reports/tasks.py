import logging

from django.conf import settings
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

from qatrack.qatrack_core.email import send_email_to_users
from qatrack.qatrack_core.tasks import run_periodic_scheduler
from qatrack.reports.models import ReportSchedule
from qatrack.reports.reports import CONTENT_TYPES

logger = logging.getLogger('qatrack')


def run_reports():
    """Should run every 15 minutes at HH:07:30, HH:22:30, HH:37:30, HH:52:30"""

    run_periodic_scheduler(
        ReportSchedule, "run_reports", schedule_report, time_field="time", recurrence_field="schedule"
    )


def schedule_report(s, send_time):

    logger.info("Scheduling report %s for %s" % (s.report_id, send_time))
    name = "Send report %d %s" % (s.report_id, send_time.isoformat())
    schedule(
        "qatrack.reports.tasks.send_report",
        s.id,
        name,
        name=name,
        schedule_type=Schedule.ONCE,
        repeats=1,
        next_run=send_time,
        task_name=name,
    )


def send_report(schedule_id, task_name=""):

    logger.info("Attempting Send of ReportSchedule %s" % schedule_id)

    s = ReportSchedule.objects.filter(id=schedule_id).first()
    if s:
        recipients = s.recipients()
        if not recipients:
            logger.info("Send of ReportSchedule %s requested, but no recipients" % schedule_id)
            return
    else:
        logger.info("Send of ReportSchedule %s requested, but no such ReportSchedule exists" % schedule_id)
        return

    fname, attach = s.report.render()

    try:
        send_email_to_users(
            recipients,
            "reports/email.html",
            context={'report': s.report, "report_schedule": s},
            subject_template="reports/email_subject.txt",
            text_template="reports/email.txt",
            attachments=[(fname, attach, CONTENT_TYPES[s.report.report_format])],
        )
        logger.info("Sent ReportSchedule %s (report %s) at %s" % (schedule_id, s.report_id, timezone.now()))
        try:
            Schedule.objects.get(name=task_name).delete()
        except:  # noqa: E722  # pragma: nocover
            logger.exception("Unable to delete Schedule.name = %s after successful send" % task_name)
    except:  # noqa: E722  # pragma: nocover
        logger.exception(
            "Error sending email for ReportSchedule %s (report %s) at %s." % (schedule_id, s.report_id, timezone.now())
        )
        fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        if not fail_silently:
            raise
    finally:
        s.last_sent = timezone.now()
        s.save()
