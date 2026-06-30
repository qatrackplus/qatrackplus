import calendar
import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from django.utils.formats import get_format


def date_to_datetime(date_obj):
    """If passed a date object will return an equivalent datetime at 00:00 in the current timezone"""
    if isinstance(date_obj, datetime.date) and not isinstance(date_obj, datetime.datetime):
        tz = ZoneInfo(settings.TIME_ZONE)
        return timezone.datetime(date_obj.year, date_obj.month, date_obj.day).replace(tzinfo=tz)
    return date_obj


def start_of_day(dt, naive=False):
    """convert datetime to start of day in local timezone"""
    if naive:
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    tz = ZoneInfo(settings.TIME_ZONE)
    return dt.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt, naive=False):
    """convert datetime to end of day in local timezone"""
    if naive:
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    tz = ZoneInfo(settings.TIME_ZONE)
    return dt.astimezone(tz).replace(hour=23, minute=59, second=59, microsecond=999999)


def month_start_and_end(year, month):
    """Return start, end tuple of datetimes representing the start and end of input year/month"""
    tz = ZoneInfo(settings.TIME_ZONE)
    start = timezone.datetime(year, month, 1).replace(tzinfo=tz)
    end = timezone.datetime(year, month, calendar.monthrange(year, month)[1]).replace(tzinfo=tz)
    return start, end


def last_month_dates(dt=None):
    """Return the start and end datetimes of the month before either the input
    datetime or timezone.now() if dt=None"""

    dt = dt or timezone.now()
    month, year = (12, dt.year - 1) if dt.month == 1 else (dt.month - 1, dt.year)
    return month_start_and_end(year, month)


def format_datetime(dt, fmt=settings.DATETIME_INPUT_FORMATS[0]):
    """Take a date time and return as string formatted date time after converting to localtime"""

    if not dt:
        return ""

    if isinstance(dt, timezone.datetime) and timezone.is_aware(dt):
        dt = timezone.localtime(dt)

    return dt.strftime(fmt)


def format_as_date(dt, fmt=settings.DATE_INPUT_FORMATS[0]):
    """Take a date time and return as string formatted date after converting to localtime"""
    return format_datetime(dt, fmt=fmt)


def format_as_time(dt, fmt=settings.TIME_INPUT_FORMATS[0]):
    return format_datetime(dt, fmt=fmt)


def format_timedelta(td):
    return "" if td is None else str(td)


def parse_datetime(dt_str):
    """Take string and return datetime object"""
    for fmt in get_format("DATETIME_INPUT_FORMATS"):
        try:
            return timezone.datetime.strptime(dt_str, fmt)
        except (ValueError, TypeError):
            continue


def round_to_next_minute(dt):
    """Round a datetime up to the nearest minute"""
    return dt.replace(second=0) + timezone.timedelta(minutes=1)


def parse_date(dt_str, as_date=True):
    """Take a string and return date object"""
    for fmt in get_format("DATE_INPUT_FORMATS"):
        try:
            dt = timezone.datetime.strptime(dt_str, fmt)
            if as_date:
                dt = dt.date()
            return dt
        except (ValueError, TypeError):
            continue


def local_end_of_day(dt=None):
    """returns end of day (11:59:59.999999 PM) in local time zone"""
    if dt is None:
        dt = timezone.now()

    tz = ZoneInfo(settings.TIME_ZONE)
    dt_local = dt.astimezone(tz)
    dt_eod = end_of_day(dt_local, naive=True)
    return dt_eod.replace(tzinfo=tz)


def local_start_of_day(dt=None):
    """returns start of day (12:00:00 AM) in local time zone"""
    if dt is None:
        dt = timezone.now()

    tz = ZoneInfo(settings.TIME_ZONE)
    dt_local = dt.astimezone(tz)
    dt_sod = start_of_day(dt_local, naive=True)
    return dt_sod.replace(tzinfo=tz)
