import os
import subprocess
import uuid
from io import BytesIO
from pathlib import Path

from dateutil import relativedelta as rdelta
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class PdfGenerationError(Exception):
    """A report PDF could not be produced."""


class ChromeNotFound(PdfGenerationError):
    """No usable Chrome/Chromium executable is configured."""


class ChromePdfFailed(PdfGenerationError):
    """Chrome was runnable but did not produce a PDF."""


PAPER_SIZES = ("letter", "a4")


def clean_paper_size(paper_size):
    """Validate a paper size before it is interpolated into a CSS declaration.

    Without this check an unexpected value would not fail - it would be
    interpolated into the `@page` rule and quietly change the rendered
    document. The web UI cannot send one (the model field carries `choices`
    and the form validates against them), but this is reachable from
    management commands and scheduled reports, and a silently mis-rendered QC
    record is a poor failure mode, so it raises instead.
    """
    cleaned = (paper_size or "letter").strip().lower()
    if cleaned not in PAPER_SIZES:
        raise ValueError(
            "unsupported paper size %r - expected one of %s"
            % (paper_size, ", ".join(PAPER_SIZES))
        )
    return cleaned


def file_uri(path):
    """A `file://` URI for a filesystem path, for the PDF engines' asset fetches.

    Concatenating `"file://" + path` is wrong on Windows. Everything between the
    two slashes and the next one is the URI's *authority*, so `file://D:\\x\\y`
    names a host of `D:\\x\\y` with an empty path, and the drive and folders are
    simply gone. WeasyPrint reports each such link as
    `URLError: [WinError 3] The system cannot find the path specified` and renders
    the report with no stylesheets and no logo. Chrome happens to accept the
    malformed form, which is why this went unnoticed for as long as Chrome was
    the only engine that could run on Windows at all.

    `Path.as_uri()` gives `file:///D:/x/y` on Windows and `file:///srv/x` on
    POSIX, and percent-encodes spaces and the like. It requires an absolute
    path, so a relative STATIC_ROOT is made absolute first - which is what the
    old concatenation effectively did too, just without saying so.
    """
    if not path:
        return ""
    return Path(path).absolute().as_uri()


def chrome_available():
    """Whether a Chrome/Chromium executable is configured and present."""
    return bool(settings.CHROME_PATH) and os.path.exists(settings.CHROME_PATH)


#: What to do about a WeasyPrint that will not load. Both branches below need it,
#: and the Windows half is not guessable from the failure: the missing pieces are
#: the same system libraries, but there they surface as a GLib load error that no
#: amount of installing the Python package fixes.
WEASYPRINT_INSTALL_HINT = (
    "WeasyPrint needs Pango, cairo and harfbuzz installed as system packages, not "
    "just the Python package. On Windows that means a GTK runtime (MSYS2's UCRT64 "
    "packages, for instance) and the WEASYPRINT_DLL_DIRECTORIES environment "
    "variable pointing at its bin directory."
)


def weasyprint_import_error():
    """The exception importing WeasyPrint raises here, or None if it imports.

    Catches OSError as well as ImportError: WeasyPrint is a cffi wrapper
    around Pango, cairo and harfbuzz, which are system packages rather than
    Python ones. Where they are absent - python:*-slim images, most notably -
    the import fails with OSError, not ImportError.

    The exception itself is returned rather than discarded because it is the
    only thing that says which library is missing. On Windows the failure is
    "cannot load library 'libgobject-2.0-0'", which names GLib and not any of
    the three packages a bare "cannot load" message would send you after.
    """
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError) as e:
        return e
    return None


def weasyprint_available():
    """Whether WeasyPrint can actually render here."""
    return weasyprint_import_error() is None


def html_to_pdf(html, name="", paper_size="letter"):
    """Render html to PDF with whichever engine is configured and usable.

    settings.PDF_ENGINE selects:

      "auto"        Chrome if available, otherwise WeasyPrint (default)
      "chrome"      Chrome only
      "weasyprint"  WeasyPrint only

    Chrome leads in "auto" because it is what the install documentation has
    always required, what deployments already have, and what the report
    stylesheets were tuned against - so an upgrade does not silently change
    how every report looks. WeasyPrint needs no browser, which is what makes
    it the right answer for a deployment that cannot install one (#835).

    Neither engine available is an error rather than a silent fallback: a
    report that cannot be produced should say so, not arrive wrong.
    """
    engine = getattr(settings, "PDF_ENGINE", "auto")

    if engine == "chrome":
        return chrometopdf(html, name=name, paper_size=paper_size)

    if engine == "weasyprint":
        why = weasyprint_import_error()
        if why is not None:
            raise PdfGenerationError(
                "PDF_ENGINE is 'weasyprint' but WeasyPrint cannot load: %s. %s"
                % (why, WEASYPRINT_INSTALL_HINT)
            )
        return weasyprint_to_pdf(html, name=name, paper_size=paper_size)

    if engine != "auto":
        raise PdfGenerationError(
            "Unknown PDF_ENGINE %r - expected 'auto', 'chrome' or 'weasyprint'." % engine
        )

    if chrome_available():
        return chrometopdf(html, name=name, paper_size=paper_size)

    if weasyprint_available():
        return weasyprint_to_pdf(html, name=name, paper_size=paper_size)

    raise PdfGenerationError(
        "No PDF engine is available. Either set CHROME_PATH to a browser, or make "
        "WeasyPrint loadable - it fails here with: %s. %s PDF_ENGINE can pin a "
        "specific engine." % (weasyprint_import_error(), WEASYPRINT_INSTALL_HINT)
    )

def site_base_url(site=None):
    """The Site's absolute base URL, with exactly one scheme on the front.

    A Site domain is documented as a bare host ("example.com"), but setting it
    to a full URL ("https://example.com") is common and this codebase already
    accommodates it - see qatrack_core.email.email_context. Prepending
    settings.HTTP_OR_HTTPS unconditionally turns that into
    "http://https://example.com", which browsers read as host "https" with the
    real host pushed into the path, so the link does not resolve.

    Callers get the base with no trailing slash, so joining a path that starts
    with "/" needs no special casing.

    Pass `site` when the caller already has one, to avoid fetching it twice.
    """
    from django.contrib.sites.models import Site

    if site is None:
        site = Site.objects.get_current()
    domain = site.domain.strip().rstrip("/")
    # URI schemes are case-insensitive (RFC 3986), so compare a lowered copy
    # while returning the domain as configured. Without this, "HTTPS://host"
    # looks like a bare host and gets a second scheme prepended - the exact
    # failure this helper exists to prevent.
    if domain.lower().startswith(("http://", "https://")):
        return domain
    return "%s://%s" % (settings.HTTP_OR_HTTPS, domain)


def weasyprint_to_pdf(html, name="", paper_size="letter"):
    """Convert HTML to PDF using WeasyPrint with proper paper size support

    Args:
        html: HTML content to convert
        name: Unused, kept for signature compatibility with chrometopdf
        paper_size: Paper size for PDF ('letter' or 'a4')
    """
    try:
        from weasyprint import HTML
    except ImportError:
        raise ImportError("WeasyPrint not installed. Install with: uv pip install weasyprint")

    # The report templates link the real bootstrap/adminlte print stylesheets
    # and include reports/pdf.css themselves, so the only thing to add here is
    # the page size - and it is added the same way Chrome gets it, through
    # set_paper_size(), so there is one mechanism rather than one per engine.
    # Margins come from reports/pdf.css for both engines; declaring them here
    # as well meant two sources that had to be kept in step by hand.
    #
    # Do *not* re-implement the Bootstrap grid here: a flexbox `.row` stops
    # WeasyPrint from fragmenting its contents across pages, which silently
    # truncates any report containing a forced page break (see
    # reports/pdf.css).
    pdf = BytesIO()
    HTML(string=set_paper_size(html, paper_size)).write_pdf(pdf)
    return pdf.getvalue()


def set_paper_size(html, paper_size="letter"):
    """Return html with an `@page { size: ... }` rule appended to its head.

    Chrome has no command line switch for the print-to-pdf paper size -- the
    `--print-to-pdf-paper-format` we used to pass is not a recognised flag and
    silently did nothing, so every report came out Letter regardless of what
    the user picked.  CSS is the only lever that works, and it has to come
    after reports/pdf.css so it wins the cascade against its `@page` block.
    """
    rule = "<style>@page { size: %s; }</style>" % clean_paper_size(paper_size)
    if "</head>" in html:
        return html.replace("</head>", "%s</head>" % rule, 1)
    return rule + html


def chrometopdf(html, name="", paper_size="letter"):
    """use headles chrome to convert an html document to pdf

    Args:
        html: HTML content to convert
        name: Optional name for temporary files
        paper_size: Paper size for PDF ('letter' or 'a4')
    """

    tmp_html = None
    out_file = None
    out_path = None      # the finally below cleans by path, so it must always exist

    try:

        if not name:
            name = uuid.uuid4().hex[:10]

        fname = "%s_%s.html" % (name, uuid.uuid4().hex[:10])
        path = os.path.join(settings.TMP_REPORT_ROOT, fname)
        out_path = "%s.pdf" % path

        tmp_html = open(path, "wb")
        tmp_html.write(set_paper_size(html, paper_size).encode("UTF-8"))
        tmp_html.close()

        if not settings.CHROME_PATH:
            raise ChromeNotFound(
                "No Chrome/Chromium executable was found. Set CHROME_PATH in "
                "qatrack/local_settings.py to the browser to use for PDF generation."
            )

        # Passed as a sequence on every platform. On Windows this was
        # collapsed with ' '.join() first, which quotes nothing: every Chrome
        # location settings.py probes is under "C:\Program Files (x86)", and
        # TMP_REPORT_ROOT can sit under a profile directory with a space in
        # it, so both the executable and --print-to-pdf= were split on their
        # spaces before Chrome saw them. subprocess quotes a sequence itself
        # with list2cmdline(), which is what it is for. Likely a second cause
        # of #835 - a service account's temp directory is not the one a
        # deployer tests from by hand.
        command = [
            settings.CHROME_PATH,
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--print-to-pdf=%s' % out_path,
            '--print-to-pdf-no-header',
            "file://%s" % tmp_html.name,
        ]

        stderr_path = os.path.join(settings.LOG_ROOT, 'report-stderr.txt')
        stdout = open(os.path.join(settings.LOG_ROOT, 'report-stdout.txt'), 'a')
        stderr = open(stderr_path, 'a')
        try:
            status = subprocess.call(command, stdout=stdout, stderr=stderr)
        except OSError as e:
            raise ChromeNotFound(
                "Could not run '%s': %s. Check CHROME_PATH in "
                "qatrack/local_settings.py." % (settings.CHROME_PATH, e)
            )
        finally:
            stdout.close()
            stderr.close()

        # The exit status and the output file are checked separately: they
        # fail differently, and the difference is what tells a deployer
        # whether the browser is wrong or its environment is. Neither was
        # checked before - a browser that ran but produced nothing left
        # open(out_path) to raise FileNotFoundError, which the handler below
        # reported as "executable not found", pointing at the one thing that
        # was demonstrably fine. That is the symptom described in #835.
        if status != 0:
            raise ChromePdfFailed(
                "'%s' exited with status %d without producing a report. Its output "
                "is in %s." % (settings.CHROME_PATH, status, stderr_path)
            )

        if not os.path.exists(out_path):
            raise ChromePdfFailed(
                "'%s' exited cleanly but wrote no PDF to %s. A browser that does "
                "not support --print-to-pdf, or cannot write to that directory, "
                "fails exactly this way. Its output is in %s."
                % (settings.CHROME_PATH, out_path, stderr_path)
            )

        out_file = open(out_path, 'r+b')
        pdf = out_file.read()
        out_file.close()

    finally:
        if tmp_html and not tmp_html.closed:
            tmp_html.close()
        if out_file and not out_file.closed:
            out_file.close()
        try:
            if tmp_html:
                os.unlink(tmp_html.name)
        except:  # noqa: E722
            pass
        # By path, not by `out_file`: that handle is only assigned once both
        # failure branches above have passed, so a browser that exited non-zero
        # after writing a partial PDF left the file behind on every run.
        try:
            if out_path:
                os.unlink(out_path)
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

        if date_range.lower() not in self.ALL_DATE_RANGES:
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
