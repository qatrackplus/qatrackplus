import os
from subprocess import PIPE, Popen
import tempfile

from django.conf import settings
from django.utils import timezone


def chrometopdf(html, name=""):
    """use headles chrome to convert an html document to pdf"""

    try:

        if name:
            path = os.path.join(tempfile.gettempdir(), name + ".html")
            tmp_html = open(path, "wb")
        else:
            tmp_html = tempfile.NamedTemporaryFile(suffix=".html", delete=False)

        tmp_html.write(html.encode("UTF-8"))
        tmp_html.flush()

        out_file = tempfile.NamedTemporaryFile(prefix=tmp_html.name, suffix=".pdf", delete=True)

        command = [
            settings.CHROME_PATH, '--headless', '--disable-gpu',
            '--print-to-pdf=%s' % out_file.name,
            "file://%s" % tmp_html.name
        ]

        p = Popen(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()

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


def format_datetime_as_date(dt, fmt=settings.MONTH_ABBR_DATE_FORMAT):
    """Take a date time and return as string formatted date after converting to localtime"""

    if not dt:
        return ""

    if isinstance(dt, timezone.datetime) and timezone.is_aware(dt):
        dt = timezone.localtime(dt)

    return dt.strftime(fmt)


def format_datetime(dt):
    """Take a date time and return as string formatted date time after converting to localtime"""

    return format_datetime_as_date(dt, fmt=settings.MONTH_ABBR_DATETIME_FORMAT)


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
