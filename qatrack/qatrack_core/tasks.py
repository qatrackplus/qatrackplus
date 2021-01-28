from functools import wraps
import logging
import os

from django.conf import settings
from django.db import ProgrammingError, connection
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

from qatrack.qatrack_core.utils import today_start_end

logger = logging.getLogger('django-q')


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
    start_today = start_today.replace(tzinfo=None)
    end_today = end_today.replace(tzinfo=None)
    now = timezone.localtime(timezone.now()).replace(tzinfo=None)
    start_time, end_time = (now, now + timezone.timedelta(minutes=15))

    logger.info("Running %s task at %s for notices between %s and %s" % (log_name, now, start_time, end_time))

    # first narrow down notices to those supposed to run in this 15 minute block
    instances = model.objects.filter(
        **{
            "%s__gte" % time_field: start_time.strftime("%H:%M"),
            "%s__lte" % time_field: end_time.strftime("%H:%M"),
        }
    )

    if settings.DEBUG:  # pragma: nocover
        instances = model.objects.all()

    # now look at recurrences occuring today and see if they should be sent now
    for instance in instances:

        # since our recurrence can only occur with a maximum frequency of 1 /
        # day, between will just return ~timezone.now() if the report is to be
        # sent today.  If we make reports available at a higher frequency this
        # check will need to be adjusted.
        occurences = getattr(instance, recurrence_field).between(start_today, end_today)
        logger.info(
            "Occurences for %s %s: %s (between %s & %s)" % (
                model._meta.model_name,
                instance.id,
                occurences,
                start_today,
                end_today,
            )
        )
        if occurences and start_time.time() <= getattr(instance, time_field) <= end_time.time():
            tz = timezone.get_current_timezone()
            send_time = tz.localize(timezone.datetime.combine(start_today, getattr(instance, time_field)))
            handler(instance, send_time)
