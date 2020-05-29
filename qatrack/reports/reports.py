import csv
import datetime
from io import BytesIO, StringIO
import json
from urllib.parse import quote_plus

from django.conf import settings
from django.contrib.sites.models import Site
from django.http import Http404, HttpResponse
from django.shortcuts import reverse
from django.template.loader import get_template
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
import xlsxwriter

from qatrack.qatrack_core.utils import (
    chrometopdf,
    format_as_date,
    format_datetime,
    relative_dates,
)

CSV = "csv"
XLS = "xlsx"
PDF = "pdf"

REPORT_REGISTRY = {}
CONTENT_TYPES = {
    CSV: "text/csv",
    PDF: "application/pdf",
    XLS: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
ORDERED_CONTENT_TYPES = [CSV, PDF, XLS]


def register_class(target_class):
    REPORT_REGISTRY[target_class.__name__] = target_class


def format_user(user):
    if not user:
        return ""

    return user.username if not user.email else mark_safe(
        '%s (<a href="mailto:%s">%s</a>)' % (user.username, user.email, user.email)
    )


class ReportMeta(type):

    required = ["to_table"]

    def __new__(meta, name, bases, class_dict):
        cls = type.__new__(meta, name, bases, class_dict)
        register_class(cls)

        if name != "BaseReport":
            missing = []
            for req in meta.required:
                if req not in cls.__dict__ and not any(req in b.__dict__ for b in bases):
                    missing.append(req)

            if missing:
                raise TypeError("%s is missing the following required methods: %s" % (name, ', '.join(missing)))
        return cls


class BaseReport(object, metaclass=ReportMeta):

    filter_class = None
    category = _l("General")
    description = _l("Generic QATrack+ Report")
    name = ""
    report_type = ""
    extra_form = None
    formats = [PDF, XLS, CSV]

    def __init__(self, base_opts=None, report_opts=None, user=None):
        """base_opts is dict of form:
            {'report_id': <rid|None>, 'include_signature': <bool>, 'title': str} """

        self.user = user
        self.base_opts = base_opts or {}
        self.report_opts = report_opts or {}
        if self.filter_class:
            self.filter_set = self.filter_class(self.report_opts, queryset=self.get_queryset())
        else:
            self.filter_set = None

    def get_queryset(self):
        """Some report types will want to define a get_queryset method to use with their filter_set"""
        return None

    def get_filter_form(self):
        if self.filter_set:
            return self.filter_set.form

    def filter_form_valid(self, filter_form):
        """Add any extra checks for the filter_form here.  For example,
        you may want to limit the number of objects included in a report and if
        the number of objects is too large, you would do:
            filter_form.add_error("__all__", "reduce the number of objects!")
            return False
        """
        return True

    def get_template(self, using=None):
        t = getattr(self, "template", "reports/html_report.html")
        return get_template(t, using=using)

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "QATrack Report"), report_format)

    def render(self, report_format):
        self.report_format = report_format
        try:
            content = getattr(self, "to_%s" % report_format)()
        except AttributeError:
            raise Http404("Unknown report format %s" % report_format)
        return self.get_filename(report_format), content

    def render_to_response(self, report_format):
        fname, content = self.render(report_format)
        response = HttpResponse(content, content_type=CONTENT_TYPES[report_format])
        response['Content-Disposition'] = 'attachment; filename="%s"' % fname
        return response

    @property
    def html(self):
        """return whether or not this is a plain text report (csv/txt)"""
        return self.report_format in ['pdf', 'html']

    @property
    def plain(self):
        """return whether or not this is a plain text report (csv/txt)"""
        return not self.html

    def get_context(self):
        name = self.get_report_type_name()
        return {
            'STATIC_ROOT': settings.STATIC_ROOT,
            'site': Site.objects.get_current(),
            'content': "",
            'protocol': settings.HTTP_OR_HTTPS,
            'report_name': name,
            'report_description': self.description,
            'report_type': self.get_report_type(),
            'report_format': getattr(self, "report_format", "html"),
            'report_title': self.base_opts.get("title", name),
            'report_url': self.get_report_url(),
            'report_details': self.get_report_details(),
            'queryset': self.filter_set.qs if self.filter_set else None,
            'include_signature': self.base_opts.get("include_signature", False),
        }

    def make_url(self, url, text='', title='', plain=False):

        slash = "/" if not (self.domain.endswith("/") or url.startswith("/")) else ""
        full_url = '%s://%s%s%s' % (settings.HTTP_OR_HTTPS, self.domain, slash, url)
        if plain or self.plain:
            return full_url

        return mark_safe('<a href="%s" title="%s">%s</a>' % (full_url, title, text))

    def get_report_url(self):
        from qatrack.reports.forms import serialize_report
        domain = Site.objects.get_current().domain
        base_url = '%s://%s%s' % (settings.HTTP_OR_HTTPS, domain, reverse("reports"))

        if self.base_opts.get('report_id'):
            return "%s?report_id=%s" % (base_url, self.base_opts['report_id'])

        opts = serialize_report(self)
        return "%s?opts=%s" % (base_url, quote_plus(json.dumps(opts)))

    @property
    def domain(self):
        if not hasattr(self, "_domain"):
            self._domain = Site.objects.get_current().domain
        return self._domain

    def get_report_type_name(self):
        return self.name

    def get_report_type(self):
        return self.report_type

    def get_report_details(self):

        if self.filter_set is None:
            return []

        form = self.filter_set.form
        form.is_valid()
        details = []
        for name, field in form.fields.items():
            val = form.cleaned_data.get(name)
            getter = getattr(self, "get_%s_details" % name, None)
            if getter:
                try:
                    label, field_details = getter(val)
                except ValueError:  # pragma: no cover
                    raise ValueError("get_%s_details should return a 2-tuple of form (label:str, details:str)" % name)

                details.append((label, field_details))
            else:
                details.append((field.label, self.default_detail_value_format(val)))

        return details

    def default_detail_value_format(self, val):
        """Take a value and return as a formatted string based on its type"""

        if val is None:
            msg = "No Filter"
            return "<em>%s</em>" % msg if self.report_format not in [XLS, CSV] else msg

        if isinstance(val, str):
            if val.lower() in relative_dates.ALL_DATE_RANGES:
                start, end = relative_dates(val).range()
                return "%s (%s - %s)" % (val, format_as_date(start), format_as_date(end))
            return val

        if isinstance(val, timezone.datetime):
            return format_as_date(val)

        try:
            if len(val) > 0 and isinstance(val[0], timezone.datetime):
                joiner = " - " if len(val) == 2 else ", "
                return joiner.join(format_as_date(dt) for dt in val)
        except:  # noqa: E722  # pragma: no cover
            pass

        try:
            return ', '.join(str(x) for x in val)
        except:  # noqa: E722  # pragma: no cover
            pass

        return str(val)

    def to_html(self):
        self.report_format = "html"
        context = self.get_context()
        context['base_template'] = "reports/html_report.html"
        template = self.get_template(using=None)
        return template.render(context)

    def to_pdf(self):
        fname = self.get_filename("pdf")
        context = self.get_context()
        context['base_template'] = "reports/pdf_report.html"
        template = self.get_template(using=None)
        content = template.render(context)
        return chrometopdf(content, name=fname)

    def to_csv(self):
        context = self.get_context()
        f = StringIO()
        writer = csv.writer(f)
        for row in self.to_table(context):
            writer.writerow(row)
        f.seek(0)
        return f

    def to_xlsx(self):
        context = self.get_context()
        f = BytesIO()
        wb = xlsxwriter.Workbook(f, {'in_memory': True})
        ws = wb.add_worksheet(name="Report")
        row = 0
        col = 0
        for data_row in self.to_table(context):
            for data in data_row:

                # excel doesn't like urls longer than 255 chars, so write as string instead
                if isinstance(data, str) and "http" in data and len(data) > 255:
                    ws.write_string(row, col, data)
                elif isinstance(data, timezone.datetime):
                    ws.write_string(row, col, format_datetime(data))
                elif isinstance(data, datetime.date):
                    ws.write_string(row, col, format_as_date(data))
                else:
                    try:
                        ws.write(row, col, data)
                    except TypeError:
                        ws.write(row, col, str(data))

                col += 1
            row += 1
            col = 0

        wb.close()
        f.seek(0)
        return f

    def to_table(self, context):
        """This function should be overridden in subclasses and then used like

            class FooReport(BaseReport):
                ...
                def to_table(self, context):

                    # get default rows including description/filters etc
                    rows = super().to_table()

                    # report specific data
                    rows += [
                        [...],
                    ]
        """

        rows = [
            [_("Report Title:"), context['report_title']],
            [_("View On Site:"), self.get_report_url()],
            [_("Report Type:"), context['report_name']],
            [_("Report Description:"), context['report_description']],
            [_("Generated:"), format_datetime(timezone.now())],
            [],
            ["Filters:"],
        ]

        for label, criteria in context['report_details']:
            rows.append([label + ":", criteria])

        return rows


def report_types():
    """Return all report classes in the report registry"""
    return [ReportClass for name, ReportClass in REPORT_REGISTRY.items() if name != "BaseReport"]


def report_descriptions():
    """
    Return dictionary of form {report_type: description} for all report classes
    in the report registry
    """

    return {r.report_type: mark_safe(r.description) for r in report_types()}


def report_class(report_type):
    """Return report class corresponding to input report_type"""

    for r in report_types():
        if r.report_type == report_type:
            return r
    raise ValueError("Report class '%s' not found" % report_type)


def report_categories():
    """return list of all available report categories"""
    return list(sorted(set([rt.category for rt in report_types()])))


def report_type_choices():
    """Return list of report type choices grouped by category. Suitable for choices for form field"""

    rts = report_types()
    rcs = report_categories()
    return [(c, [(rt.report_type, rt.name) for rt in rts if rt.category == c]) for c in rcs]
