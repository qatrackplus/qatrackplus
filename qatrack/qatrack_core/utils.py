import os
import subprocess
import uuid

from dateutil import relativedelta as rdelta
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


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
        tmp_html.close()

        command = [
            settings.CHROME_PATH,
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--print-to-pdf=%s' % out_path,
            "file://%s" % tmp_html.name,
        ]

        if os.name.lower() == "nt":
            command = ' '.join(command)

        stdout = open(os.path.join(settings.LOG_ROOT, 'report-stdout.txt'), 'a')
        stderr = open(os.path.join(settings.LOG_ROOT, 'report-stderr.txt'), 'a')
        subprocess.call(command, stdout=stdout, stderr=stderr)

        out_file = open(out_path, 'r+b')
        pdf = out_file.read()
        out_file.close()

    except OSError:
        raise OSError("chrome '%s' executable not found" % (settings.CHROME_PATH))
    finally:
        if not tmp_html.closed:
            tmp_html.close()
        if not out_file.closed:
            out_file.close()
        try:
            os.unlink(tmp_html.name)
        except:  # noqa: E722
            pass

    return pdf


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


def today_start():
    """Return datetime representing start of today"""
    now = timezone.localtime(timezone.now())
    return start_of_day(now)


def today_end():
    """Return datetime representing start of today"""
    now = timezone.localtime(timezone.now())
    return end_of_day(now)


class relative_dates:

    FUTURE_RANGES = [
        "next 7 days",
        "next 30 days",
        "next 90 days",
        "next 180 days",
        "next 365 days",
        "this week",
        "this month",
        "this year",
        "next week",
        "next month",
        "next 3 months",
        "next 6 months",
        "next year",
        "today",
    ]

    PAST_RANGES = [
        "today",
        "last 7 days",
        "last 30 days",
        "last 90 days",
        "last 180 days",
        "last 365 days",
        "this week",
        "this month",
        "this year",
        "last week",
        "last month",
        "last 3 months",
        "last 6 months",
        "last year",
    ]

    ALL_DATE_RANGES = PAST_RANGES + FUTURE_RANGES

    def __init__(self, date_range, pivot=None):
        """
        Initialize a relative_dates object.

        date_range is a string from PAST_RANGES/FUTURE_RANGES and times for
        start_dt & end_dt are start of day and end of day respectively.

        Example Usage:

            rd = relative_dates("next 7 days")
            start_dt, end_dt = rd.range

            pivot = timezone.now() + timezone.timedelta(days=4)
            rd = relative_dates("next 7 days", pivot=pivot)
            start_dt = rd.start
            end_dt = rd.end
        """

        if not date_range.lower() in self.ALL_DATE_RANGES:
            raise ValueError("%s is not a valid date range string")

        self.date_range = date_range.strip().lower()

        self.pivot = (pivot or timezone.now()).astimezone(timezone.get_current_timezone())

    def range(self):

        if self.date_range.startswith("today"):
            return start_of_day(self.pivot), end_of_day(self.pivot)
        elif self.date_range.startswith("next"):
            return self._next_interval()
        elif self.date_range.startswith("this"):
            return self._this_interval()
        elif self.date_range.startswith("last"):
            return self._last_interval()

    def start(self):
        return self.range()[0]

    def end(self):
        return self.range()[1]

    def _next_interval(self):

        dr = self.date_range

        if 'days' in dr:
            __, num, interval = dr.split()
            start = start_of_day(self.pivot)
            end = end_of_day(start + timezone.timedelta(days=int(num)))
        elif 'week' in dr:
            start = start_of_day(self.pivot) + rdelta.relativedelta(days=1, weekday=rdelta.SU)
            end = end_of_day(self.pivot) + rdelta.relativedelta(days=7, weekday=rdelta.SA)
        elif 'months' in dr:
            __, num, interval = dr.split()
            start = start_of_day(self.pivot) + rdelta.relativedelta(months=1, day=1)
            end = end_of_day(self.pivot) + rdelta.relativedelta(months=int(num), day=31)
        elif 'month' in dr:
            start = start_of_day(self.pivot) + rdelta.relativedelta(months=1, day=1)
            end = end_of_day(self.pivot) + rdelta.relativedelta(months=1, day=31)
        elif 'year' in dr:
            start = start_of_day(self.pivot) + rdelta.relativedelta(years=1, month=1, day=1)
            end = end_of_day(self.pivot) + rdelta.relativedelta(years=1, month=12, day=31)
        return start, end

    def _this_interval(self):
        dr = self.date_range

        if 'days' in dr:
            __, num, interval = dr.split()
            start = start_of_day(self.pivot)
            end = end_of_day(start + timezone.timedelta(days=int(num)))
        elif 'week' in dr:
            start = start_of_day(self.pivot) + rdelta.relativedelta(weekday=rdelta.SU(-1))
            end = end_of_day(self.pivot) + rdelta.relativedelta(weekday=rdelta.SA(1))
        elif 'months' in dr:
            __, num, interval = dr.split()
            start = start_of_day(self.pivot) + rdelta.relativedelta(months=1, day=1)
            end = end_of_day(self.pivot) + rdelta.relativedelta(months=int(num), day=31)
        elif 'month' in dr:
            start = start_of_day(self.pivot) + rdelta.relativedelta(months=0, day=1)
            end = end_of_day(self.pivot) + rdelta.relativedelta(months=0, day=31)
        elif 'year' in dr:
            start = start_of_day(self.pivot) + rdelta.relativedelta(month=1, day=1)
            end = end_of_day(self.pivot) + rdelta.relativedelta(month=12, day=31)

        return start, end

    def _last_interval(self):

        dr = self.date_range

        if 'days' in dr:
            __, num, interval = dr.split()
            end = end_of_day(self.pivot)
            start = start_of_day(end + timezone.timedelta(days=-int(num)))
        elif 'week' in dr:
            start = start_of_day(self.pivot) + rdelta.relativedelta(weekday=rdelta.SU(-2))
            end = end_of_day(self.pivot) + rdelta.relativedelta(weeks=-1, weekday=rdelta.SA(1))
        elif 'months' in dr:
            __, num, interval = dr.split()
            start = start_of_day(self.pivot) + rdelta.relativedelta(months=-int(num), day=1)
            end = end_of_day(self.pivot) + rdelta.relativedelta(months=-1, day=31)
        elif 'month' in dr:
            start = start_of_day(self.pivot) + rdelta.relativedelta(months=-1, day=1)
            end = end_of_day(self.pivot) + rdelta.relativedelta(months=-1, day=31)
        elif 'year' in dr:
            start = start_of_day(self.pivot) + rdelta.relativedelta(years=-1, month=1, day=1)
            end = end_of_day(self.pivot) + rdelta.relativedelta(years=-1, month=12, day=31)
        return start, end


def unique_slug_generator(instance, text, manager=None):
    """Take in a model manager (e.g. Unit.objects) and a text value and generate
    a unique slug based on the text"""

    klass = instance._meta.model
    manager = manager or klass.objects

    append = 0
    while True:
        append_text = "-%d" % append if append > 0 else ""
        slug = slugify(text + append_text)
        if manager.exclude(id=instance.id).filter(slug=slug):
            append += 1
        else:
            break
    return slug
