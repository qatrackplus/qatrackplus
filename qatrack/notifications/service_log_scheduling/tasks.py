import logging

from django.conf import settings
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

from qatrack.notifications.models import ServiceEventSchedulingNotice
from qatrack.qatrack_core.email import send_email_to_users
from qatrack.qatrack_core.tasks import run_periodic_scheduler

logger = logging.getLogger('django-q2')


def run_scheduling_notices():
    run_periodic_scheduler(
        ServiceEventSchedulingNotice,
        'run_service_log_scheduling_notices',
        schedule_service_event_scheduling_notice,
        time_field='time',
        recurrence_field='recurrences',
    )


def schedule_service_event_scheduling_notice(notice, send_time):
    logger.info(f'Service Event Scheduling notification {notice.pk} for {send_time}')
    name = 'Send notification %d %s' % (notice.pk, send_time.isoformat())

    schedule(
        'qatrack.notifications.service_log_scheduling.tasks.send_scheduling_notice',
        notice.id,
        name,
        name=name,
        schedule_type=Schedule.ONCE,
        repeats=1,
        next_run=send_time,
        task_name=name,
    )


def send_scheduling_notice(notice_id, task_name=''):
    notice = ServiceEventSchedulingNotice.objects.filter(id=notice_id).first()

    if notice:
        if not notice.send_required():
            logger.info(
                f'Send of ServiceEventSchedulingNotice {notice_id} requested, but no Service Event Schedules to notify about'
            )  # noqa: E501
            return

        recipients = notice.recipients.recipient_emails()
        if not recipients:
            logger.info(f'Send of ServiceEventSchedulingNotice {notice_id} requested, but no recipients')
            return
    else:
        logger.info(
            f'Send of ServiceEventSchedulingNotice {notice_id} requested, but no such ServiceEventSchedulingNotice exists'
        )  # noqa: E501
        return

    try:
        send_email_to_users(
            recipients,
            'service_log_scheduling/email.html',
            context={'notice': notice},
            subject_template='service_log_scheduling/subject.txt',
            text_template='service_log_scheduling/email.txt',
        )
        logger.info(f'Sent ServiceEventSchedulingNotice {notice_id} at {timezone.now()}')
        try:
            Schedule.objects.get(name=task_name).delete()
        except:  # noqa: E722  # pragma: nocover
            logger.exception(f'Unable to delete Schedule.name = {task_name} after successful send')
    except:  # noqa: E722  # pragma: nocover
        logger.exception(f'Error sending email for ServiceEventSchedulingNotice {notice_id} at {timezone.now()}.')

        fail_silently = getattr(settings, 'EMAIL_FAIL_SILENTLY', True)
        if not fail_silently:
            raise
    finally:
        notice.last_sent = timezone.now()
        notice.save()
