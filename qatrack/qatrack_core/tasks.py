import logging
import os
from functools import wraps
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import ProgrammingError, connection
from django.db.models import Q
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

from qatrack.qatrack_core.utils import today_start_end

logger = logging.getLogger('django-q2')


def qatrack_task_wrapper(func):

    @wraps(func)
    def wrapped(*args, **kwargs):
        if os.name.lower() == "nt":
            try:
                connection.cursor()
            except ProgrammingError:
                connection.connect()
        return func(*args, **kwargs)

    return wrapped


def _schedule_periodic_task(function, task_name, interval_min=None, next_run=None, schedule_type=Schedule.MINUTES):
    """Create a periodic schedule calling input function.  Default interval is 15min"""

    if schedule_type == Schedule.MINUTES and interval_min is None:
        interval_min = 15

    now = timezone.now()

    if next_run is None:
        # set initial schedule to 7.5 minutes after then next quarter hour
        # the schedule will then run every 15 minutes at HH:07:30, HH:22:30, HH:37:30, HH:52:30
        next_run = now.replace(
            minute=0, second=0, microsecond=0
        ) + timezone.timedelta(seconds=int(interval_min * 60 / 2.))

        while next_run < now:
            next_run += timezone.timedelta(minutes=interval_min)

    try:

        sch = Schedule.objects.get(name=task_name)
        sch.func = function
        sch.minutes = interval_min
        sch.next_run = next_run
        sch.save()
        logger.info("%s next run updated to %s" % (function, next_run))

    except Schedule.DoesNotExist:

        schedule(
            function,
            name=task_name,
            schedule_type=schedule_type,
            minutes=interval_min,
            repeats=-1,
            next_run=next_run,
        )
        logger.info("%s schedule created and next run set to %s" % (function, next_run))


@qatrack_task_wrapper
def run_periodic_scheduler(model, log_name, handler, time_field="time", recurrence_field="recurrence"):
    """Check a model with a recurring schedule for instances that should be run in the next time period.

        model: the Django model to check,

        log_name: short description to include in log strings,

        handler: a function that will be called when an instance should be run
        in the current time period must accept an instance of model, and a
        datetime when the task should be scheduled for. The handler function
        should perform the actual scheduling of the task.

        time_field: The name of the field that holds what time the task should be run
        recurrence_field: The name of the field that holds the recurrence field
    """

    start_today, end_today = today_start_end()
    now = timezone.localtime(timezone.now()).replace(tzinfo=None)
    start_time, end_time = (now, now + timezone.timedelta(minutes=15))

    logger.info("Running %s task at %s for notices between %s and %s" % (log_name, now, start_time, end_time))

    # first narrow down notices to those supposed to run in this 15 minute block
    start_time_str = start_time.strftime("%H:%M")
    end_time_str = end_time.strftime("%H:%M")

    if start_time_str <= end_time_str:
        instances = model.objects.filter(
            **{
                "%s__gte" % time_field: start_time_str,
                "%s__lte" % time_field: end_time_str,
            }
        )
    else:
        instances = model.objects.filter(
            Q(**{"%s__gte" % time_field: start_time_str}) |
            Q(**{"%s__lte" % time_field: end_time_str})
        )

    if settings.DEBUG:  # pragma: nocover
        instances = model.objects.all()

    tz = ZoneInfo(settings.TIME_ZONE)

    # now look at recurrences occuring today and see if they should be sent now
    for instance in instances:
        t = getattr(instance, time_field)

        for day_offset in (0, 1):
            target_date = start_today.date() + timezone.timedelta(days=day_offset)
            dt = timezone.datetime.combine(target_date, t)

            if start_time <= dt <= end_time:
                target_start = start_today + timezone.timedelta(days=day_offset)
                target_end = end_today + timezone.timedelta(days=day_offset)

                occurrences = getattr(instance, recurrence_field).between(target_start, target_end, inc=True)
                
                logger.info(
                    "Occurrences for %s %s: %s (between %s & %s)" % (
                        model._meta.model_name,
                        instance.id,
                        occurrences,
                        target_start,
                        target_end,
                    )
                )

                if occurrences:
                    send_time = dt.replace(tzinfo=tz)
                    handler(instance, send_time)
                
                break
