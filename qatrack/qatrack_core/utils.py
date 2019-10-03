import os
from subprocess import PIPE, Popen
import subprocess
import tempfile
import uuid

from django.conf import settings
from django.utils import timezone
from django.utils.formats import get_format


def chrometopdf(html, name=""):
    """use headles chrome to convert an html document to pdf"""

    try:

        if not name:
            name = uuid.uuid4().hex[:10]

        fname = "%s_%s.html" % (name, uuid.uuid4().hex[:10])
        path = os.path.join(settings.TMP_REPORT_ROOT, fname)
        out_path = "%s.pdf" % path

        tmp_html = open(path, "wb")
        tmp_html.write(html.encode("UTF-8"))
        tmp_html.flush()

        out_file = open(out_path, "wb")

        command = [
            settings.CHROME_PATH, '--headless', '--disable-gpu',
            '--print-to-pdf=%s' % out_file.name,
            "file://%s" % tmp_html.name
        ]

        subprocess.call(' '.join(command))

        pdf = open(out_file.name, 'r+b').read()

    except OSError:
        raise OSError("chrome '%s' executable not found" % (settings.CHROME_PATH))
    finally:
        tmp_html.close()
        out_file.close()
        try:
            os.unlink(tmp_html.name)
        except:  # noqa: E722
            pass

    return pdf


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


def parse_datetime(dt_str):
    """Take string and return datetime object"""
    for fmt in get_format("DATETIME_INPUT_FORMATS"):
        try:
            return timezone.datetime.strptime(dt_str, fmt)
        except (ValueError, TypeError):
            continue


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


def end_of_day(dt):
    """Take datetime and move forward to last microsecond of date"""

    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def start_of_day(dt):
    """Take datetime and move backward first microsecond of date"""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def today_start_end():
    """Return datetimes representing start and end of today"""
    now = timezone.localtime(timezone.now())
    return start_of_day(now), end_of_day(now)
