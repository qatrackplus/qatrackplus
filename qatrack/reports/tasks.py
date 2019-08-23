import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

from qatrack.qatrack_core.utils import format_datetime, today_start_end
from qatrack.reports.models import ReportSchedule
from qatrack.reports.reports import CONTENT_TYPES

logger = logging.getLogger('qatrack')


def _schedule_tasks():

    func = "qatrack.reports.tasks.run_reports"
    now = timezone.now()

    # set initial schedule to 7.5 minutes after then next quarter hour
    # the schedule will then run every 15 minutes at HH:07:30, HH:22:30, HH:37:30, HH:52:30
    next_run = now.replace(minute=0, second=0, microsecond=0) + timezone.timedelta(minutes=7, seconds=30)

    while next_run < now:
        next_run += timezone.timedelta(minutes=15)

    try:

        sch = Schedule.objects.get(func=func)
        sch.next_run = next_run
        sch.save()
        logger.info("%s next run updated to %s" % (func, next_run))

    except Schedule.DoesNotExist:

        schedule(
            func,
            name="QATrack+ Report Sender",
            schedule_type=Schedule.MINUTES,
            minutes=15,
            repeats=-1,
            next_run=next_run,
        )
        logger.info("%s schedule created and next run set to %s" % (func, next_run))


def run_reports():
    """Should run every 15 minutes at HH:07:30, HH:22:30, HH:37:30, HH:52:30"""

    start_today, end_today = today_start_end()
    start_today = start_today.replace(tzinfo=None)
    end_today = end_today.replace(tzinfo=None)
    now = timezone.localtime(timezone.now()).replace(tzinfo=None)
    start_time, end_time = (now, now + timezone.timedelta(minutes=15))
    logger.info("Running run_reports task at %s for reports scheduled between %s and %s" % (now, start_time, end_time))

    # first narrow down schedules to those supposed to run in this 15 minute block
    schedules = ReportSchedule.objects.filter(
        time__gte=start_time.strftime("%H:%M"),
        time__lte=end_time.strftime("%H:%M"),
    )

    if settings.DEBUG:  # pragma: nocover
        schedules = ReportSchedule.objects.all()

    # now look at recurrences occuring today and see if they should be sent now
    for s in schedules:

        # since our recurrence can only occur with a maximum frequency of 1 / day,
        # s.schedule.between will just return ~timezone.now() if the report is to be
        # sent today.  If we make reports available at a higher frequency this check
        # will need to be adjusted
        occurences = s.schedule.between(start_today, end_today)
        logger.info(
            "Occurences for report %s: %s (between %s & %s)" % (
                s.report_id,
                occurences,
                start_today,
                end_today,
            )
        )
        if occurences and start_time.time() <= s.time <= end_time.time():
            tz = timezone.get_current_timezone()
            send_time = tz.localize(timezone.datetime.combine(start_today, s.time))
            schedule_report(s, send_time)


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

    context = {'report': s.report}

    text_body = get_template("reports/email.txt").render(context)
    html_body = get_template("reports/email.html").render(context)

    from_address = getattr(settings, "EMAIL_NOTIFICATION_SENDER", "QATrack+")
    fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)

    message = EmailMultiAlternatives(
        "QATrack+ Reports: #%d - %s - %s" % (s.report_id, s.report.title, format_datetime(timezone.now())),
        text_body,
        from_address,
        recipients,
    )
    message.attach_alternative(html_body, "text/html")

    fname, attach = s.report.render()
    message.attach(fname, attach, CONTENT_TYPES[s.report.report_format])

    try:
        message.send(fail_silently=False)
        logger.info("Sent ReportSchedule %s (report %s) at %s" % (schedule_id, s.report_id, timezone.now()))
        try:
            Schedule.objects.get(name=task_name).delete()
        except:  # noqa: E722  # pragma: nocover
            logger.exception("Unable to delete Schedule.name = %s after successful send" % task_name)
    except:  # noqa: E722  # pragma: nocover
        logger.exception(
            "Error sending email for ReportSchedule %s (report %s) at %s." % (schedule_id, s.report_id, timezone.now())
        )
        if not fail_silently:
            raise
    finally:
        s.last_sent = timezone.now()
        s.save()
