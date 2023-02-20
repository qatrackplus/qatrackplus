import calendar
import datetime

from django.utils import timezone
from django.utils.formats import get_format


def date_to_datetime(date):
    """If passed a date object will return an equivalent datetime at 00:00 in the current timezone"""
    if isinstance(date, datetime.date):
        return timezone.get_current_timezone().localize(timezone.datetime(date.year, date.month, date.day))
    return date


def start_of_day(dt):
    """convert datetime to start of day in local timezone"""
    tz = timezone.get_current_timezone()
    return dt.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt):
    """convert datetime to end of day in local timezone"""
    tz = timezone.get_current_timezone()
    return dt.astimezone(tz).replace(hour=23, minute=59, second=59, microsecond=999999)


def month_start_and_end(year, month):
    """Return start, end tuple of datetimes representing the start and end of input year/month"""
    tz = timezone.get_current_timezone()
    start = tz.localize(timezone.datetime(year, month, 1))
    end = tz.localize(timezone.datetime(year, month, calendar.monthrange(year, month)[1]))
    return start, end


def last_month_dates(dt=None):
    """Return the start and end datetimes of the month before either the input
    datetime or timezone.now() if dt=None"""

    dt = dt or timezone.now()
    month, year = (12, dt.year - 1) if dt.month == 1 else (dt.month - 1, dt.year)
    return month_start_and_end(year, month)


def format_datetime(dt, fmt=get_format("DATETIME_INPUT_FORMATS")[0]):
    """Take a date time and return as string formatted date time after converting to localtime"""

    if not dt:
        return ""

    if isinstance(dt, timezone.datetime) and timezone.is_aware(dt):
        dt = timezone.localtime(dt)

    return dt.strftime(fmt)


def format_as_date(dt, fmt=get_format("DATE_INPUT_FORMATS")[0]):
    """Take a date time and return as string formatted date after converting to localtime"""
    return format_datetime(dt, fmt=fmt)


def format_as_time(dt, fmt=get_format("DATE_INPUT_FORMATS")[0]):
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
