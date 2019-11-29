import csv
import datetime
from io import BytesIO, StringIO
import json
from urllib.parse import quote_plus

from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import reverse
from django.template.loader import get_template
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
import pandas as pd
import xlsxwriter

from qatrack.qa import models
from qatrack.qa.templatetags.qa_tags import as_time_delta
from qatrack.qa.utils import end_of_day
from qatrack.qatrack_core.utils import (
    chrometopdf,
    format_as_date,
    format_datetime,
)
from qatrack.reports import filters
from qatrack.units import models as umodels

CSV = "csv"
XLS = "xlsx"
PDF = "pdf"

REPORT_REGISTRY = {}
CONTENT_TYPES = {
    CSV: "text/csv",
    PDF: "application/pdf",
    XLS: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def register_class(target_class):
    REPORT_REGISTRY[target_class.__name__] = target_class


def format_user(user):
    if not user:
        return ""

    return user.username if not user.email else "%s (%s)" % (user.username, user.email)


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
        content = getattr(self, "to_%s" % report_format)()
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
                except ValueError:
                    raise ValueError("get_%s_details should return a 2-tuple of form (label:str, details:str)" % name)

                details.append((label, field_details))
            else:
                details.append((field.label, self.default_detail_value_format(val)))

        return details

    def default_detail_value_format(self, val):
        """Take a value and return as a formatted string based on its type"""

        if val is None:
            return "<em>No Filter</em>"

        if isinstance(val, str):
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
                    ws.write(row, col, data)

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


class QCSummaryReport(BaseReport):

    report_type = "qc-summary-by-date"
    name = "QC Summary"
    filter_class = filters.TestListInstanceFilter
    description = mark_safe(_l(
        "This report lists all Test List Instances from a given time period for "
        "selected sites, units, frequencies, and groups."
    ))

    MAX_TLIS = getattr(settings, "REPORT_QCSUMMARYREPORT_MAX_TLIS", 5000)

    template = "reports/reports/qc_summary.html"

    def filter_form_valid(self, filter_form):

        ntlis = self.filter_set.qs.count()
        if ntlis > self.MAX_TLIS:
            filter_form.add_error(
                "__all__", "This report can only be generated with %d or fewer Test List "
                "Instances.  Your filters are including %d. Please reduce the "
                "number of Test List (Cycle) assignments, or Work Completed time "
                "period." % (self.MAX_TLIS, ntlis)
            )

        return filter_form.is_valid()

    def get_queryset(self):
        return models.TestListInstance.objects.all()

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "qc-summary-report"), report_format)

    def get_unit_test_collection__unit__site_details(self, val):
        sites = [x.name if x != "null" else "Other" for x in val]
        return ("Site", ", ".join(sites))

    def get_unit_test_collection__unit_details(self, val):
        units = models.Unit.objects.select_related("site").filter(pk__in=val)
        units = ('%s - %s' % (u.site.name if u.site else _("Other"), u.name) for u in units)
        return ("Unit(s)", ', '.join(units))

    def get_unit_test_collection__frequency_details(self, val):
        freqs = [x.name if x != "null" else "Ad Hoc" for x in val]
        return ("Frequencies", ", ".join(freqs))

    def get_context(self):

        context = super().get_context()

        # since we're grouping by site, we need to handle sites separately
        sites = self.filter_set.qs.order_by(
            "unit_test_collection__unit__site__name"
        ).values_list("unit_test_collection__unit__site", flat=True).distinct()

        sites_data = []

        for site in sites:

            if site:  # site can be None here since not all units may have a site
                site = umodels.Site.objects.get(pk=site)

            sites_data.append((site.name if site else "", []))

            for tli in self.get_tlis_for_site(self.filter_set.qs, site):
                sites_data[-1][-1].append({
                    'unit_name': tli.unit_test_collection.unit.name,
                    'test_list_name': tli.test_list.name,
                    'due_date': format_as_date(tli.due_date),
                    'work_completed': self.get_work_completed(tli),
                    'pass_fail': self.get_pass_fail_status(tli),
                    'link': self.make_url(tli.get_absolute_url(), plain=True),
                })

        context['sites_data'] = sites_data

        return context

    def get_tlis_for_site(self, qs, site):
        """Get Test List Instances from filtered queryset for input site"""

        tlis = qs.filter(
            unit_test_collection__unit__site=site,
        ).exclude(
            Q(work_completed=None) | Q(in_progress=True),
        )

        tlis = tlis.order_by(
            "unit_test_collection__unit__%s" % settings.ORDER_UNITS_BY,
            "unit_test_collection__name",
            "test_list__name",
            "work_completed",
        ).select_related(
            "test_list",
            "unit_test_collection",
            "unit_test_collection__unit",
            "unit_test_collection__frequency",
        ).prefetch_related("testinstance_set")

        return tlis

    def get_pass_fail_status(self, tli):
        """Format pass fail status with icons for html reports, otherwise just as plain text"""

        if self.html:
            if not hasattr(self, "_pass_fail_t"):
                self._pass_fail_t = get_template("qa/pass_fail_status.html")
            return self._pass_fail_t.render({'instance': tli, 'show_icons': True})

        return ", ".join("%d %s" % (len(t), d) for s, d, t in tli.pass_fail_status())

    def get_work_completed(self, tli):
        """Format work completed as link to instance if html report otherwise just return formatted date"""

        wc = format_as_date(tli.work_completed)

        if self.html:
            return self.make_url(tli.get_absolute_url(), wc, _("Click to view on site"))

        return wc

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        rows.append([
            _("Site"),
            _("Unit"),
            ("Test list"),
            _("Due Date"),
            _("Work Completed"),
            _("Pass/Fail Status"),
            _("Link"),
        ])

        for site, tlis in context['sites_data']:
            for tli in tlis:
                rows.append([
                    site,
                    tli['unit_name'],
                    tli['test_list_name'],
                    tli['due_date'],
                    tli['work_completed'],
                    tli['pass_fail'],
                    tli['link'],
                ])

        return rows


class UTCReport(BaseReport):

    report_type = "utc"
    name = "Test List Instances"
    filter_class = filters.UnitTestCollectionFilter
    description = mark_safe(
        _l(
            "This report includes details for all Test List Instances from a given time period for "
            "a given Unit Test List (Cycle) assignment."
        )
    )

    MAX_TLIS = getattr(settings, "REPORT_UTCREPORT_MAX_TLIS", 365)

    template = "reports/reports/utc.html"

    def filter_form_valid(self, filter_form):

        ntlis = self.filter_set.qs.count()
        if ntlis > self.MAX_TLIS:
            filter_form.add_error(
                "__all__", "This report can only be generated with %d or fewer Test List "
                "Instances.  Your filters are including %d. Please reduce the "
                "number of Test List (Cycle) assignments, or Work Completed time "
                "period." % (self.MAX_TLIS, ntlis)
            )

        return filter_form.is_valid()

    def get_queryset(self):
        return models.TestListInstance.objects.select_related("created_by")

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "unit-test-list-assignment-summary-report"), report_format)

    def get_unit_test_collection_details(self, val):
        utcs = models.UnitTestCollection.objects.filter(pk__in=val)
        return ("Unit / Test List", ', '.join("%s - %s" % (utc.unit.name, utc.name) for utc in utcs))

    def get_context(self):

        context = super().get_context()

        qs = self.filter_set.qs.select_related(
            "created_by",
            "modified_by",
            "reviewed_by",
            "test_list",
            "unit_test_collection",
            "unit_test_collection__unit",
            "unit_test_collection__content_type",
        ).prefetch_related(
            "comments",
            Prefetch("testinstance_set", queryset=models.TestInstance.objects.order_by("created")),
            "testinstance_set__unit_test_info__test",
            "testinstance_set__reference",
            "testinstance_set__tolerance",
            "testinstance_set__status",
            "testinstance_set__attachment_set",
            "attachment_set",
            "serviceevents_initiated",
            "rtsqa_for_tli",
        ).order_by("work_completed")
        context['queryset'] = qs

        form = self.get_filter_form()
        utcs = models.UnitTestCollection.objects.filter(pk__in=form.cleaned_data['unit_test_collection'])
        context['utcs'] = utcs

        context['site_name'] = ', '.join(sorted(set(utc.unit.site.name if utc.unit.site else _("N/A") for utc in utcs)))

        context['test_list_borders'] = self.get_borders(utcs)
        context['comments'] = self.get_comments(utcs)
        context['perms'] = PermWrapper(self.user)
        return context

    def get_borders(self, utcs):
        borders = {}
        for utc in utcs:
            for tl in utc.tests_object.all_lists():
                borders[tl.pk] = tl.sublist_borders()

        return borders

    def get_comments(self, utcs):
        from django_comments.models import Comment
        ct = ContentType.objects.get(model="testlistinstance").pk
        tlis = models.TestListInstance.objects.filter(
            unit_test_collection__id__in=utcs.values_list("id"),
        )

        comments_qs = Comment.objects.filter(
            content_type_id=ct,
            object_pk__in=map(str, tlis.values_list("id", flat=True)),
        ).order_by(
            "-submit_date",
        ).values_list(
            "pk",
            "submit_date",
            "user__username",
            "comment",
        )

        comments = dict((c[0], c[1:]) for c in comments_qs)
        return comments

    def to_table(self, context):

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

        for tli in context['queryset']:

            rows.extend([
                [],
                [],
                ["Test List Instance:", self.make_url(tli.get_absolute_url())],
                [_("Created By") + ":", format_user(tli.created_by)],
                [_("Work Started") + ":", format_as_date(tli.work_started)],
                [_("Work Completed") + ":", format_as_date(tli.work_completed)],
                [_("Duration") + ":", _("In Progress") if tli.in_progress else as_time_delta(tli.duration())],
                [_("Modified") + ":", format_as_date(tli.modified)],
                [_("Mofified By") + ":", format_user(tli.modified_by)],
            ])
            if tli.all_reviewed and not tli.reviewed_by:
                rows.extend(
                    [_("Reviewed") + ":", format_as_date(tli.modified)],
                    [_("Reviewed By") + ":", _("Auto Reviewed")],
                )
            else:
                rows.extend(
                    [_("Reviewed") + ":", format_as_date(tli.reviewed)],
                    [_("Reviewed By") + ":", format_user(tli.reviewed_by)],
                )

            for c in context['comments'].get(tli.pk, []):
                rows.append([_("Comment") + ":", format_datetime(c[0]), c[1], c[2]])

            for a in tli.attachment_set.all():
                rows.append([_("Attachment") + ":", a.label, self.make_url(a.attachment.url, plain=True)])

            rows.append([])
            rows.append([
                _("Test"),
                _("Value"),
                _("Reference"),
                _("Tolerance"),
                _("Pass/Fail"),
                _("Review Status"),
                _("Comment"),
                _("Attachments"),
            ])

            for ti, history in tli.history()[0]:
                row = [
                    ti.unit_test_info.test.name,
                    ti.value_display(coerce_numerical=False),
                    ti.reference.value_display() if ti.reference else "",
                    ti.tolerance.name if ti.tolerance else "",
                    ti.get_pass_fail_display(),
                    ti.status.name,
                    ti.comment,
                ]
                for a in ti.attachment_set.all():
                    row.append(self.make_url(a.attachment.url, plain=True))

                rows.append(row)

        return rows


class DueDatesReportMixin:

    def get_queryset(self):
        return models.UnitTestCollection.objects.select_related(
            "assigned_to",
            "unit",
            "frequency",
        ).exclude(active=False)

    def get_unit__site_details(self, val):
        sites = [x.name if x != "null" else _("Other") for x in val]
        return (_("Site(s)"), ", ".join(sites))

    def get_unit_details(self, val):
        units = models.Unit.objects.select_related("site").filter(pk__in=val)
        units = ('%s - %s' % (u.site.name if u.site else _("Other"), u.name) for u in units)
        return (_("Unit(s)"), ', '.join(units))

    def get_context(self):

        context = super().get_context()
        qs = self.filter_set.qs

        sites = self.filter_set.qs.order_by("unit__site__name").values_list("unit__site", flat=True).distinct()

        sites_data = []

        for site in sites:

            if site:  # site can be None here since not all units may have a site
                site = umodels.Site.objects.get(pk=site)

            sites_data.append((site.name if site else "", []))

            utcs = qs.filter(
                unit__site_id=(site if site else None),
                due_date__isnull=False,
            ).order_by("due_date", "unit__%s" % settings.ORDER_UNITS_BY)

            for utc in utcs:

                window = utc.window()
                if window:
                    window = "%s - %s" % (format_as_date(window[0]), format_as_date(window[1]))

                sites_data[-1][-1].append({
                    'utc': utc,
                    'unit_name': utc.unit.name,
                    'name': utc.name,
                    'window': window,
                    'frequency': utc.frequency.name if utc.frequency else _("Ad Hoc"),
                    'due_date': format_as_date(utc.due_date),
                    'assigned_to': utc.assigned_to.name,
                    'link': self.make_url(utc.get_absolute_url(), plain=True),
                })

        context['sites_data'] = sites_data

        return context

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        for site, site_rows in context['sites_data']:
            rows.extend([
                [],
                [],
                [site if site else _("Other")],
                [
                    _("Unit"),
                    _("Name"),
                    _("Frequency"),
                    _("Due Date"),
                    _("Window"),
                    _("Assinged To"),
                    _("Perform")
                ],
            ])

            for row in site_rows:
                rows.append([
                    row['unit_name'],
                    row['name'],
                    row['frequency'],
                    format_as_date(row['utc'].due_date),
                    row['window'],
                    row['assigned_to'],
                ])

        return rows


class NextDueDatesReport(DueDatesReportMixin, BaseReport):

    report_type = "next_due"
    name = "Next Due Dates for QC"
    filter_class = filters.SchedulingFilter
    description = mark_safe(_l("This report shows QC tests whose next due date fall in the selected time period."))

    category = _l("Scheduling")
    template = "reports/reports/next_due.html"

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or _("next-due-dates-report")), report_format)


class DueAndOverdueQCReport(DueDatesReportMixin, BaseReport):

    report_type = "due_and_overdue"
    name = "Due and Overdue QC"
    filter_class = filters.DueAndOverdueFilter
    description = mark_safe(_l("This report shows QC tests which are currently due or overdue"))

    category = _l("Scheduling")
    template = "reports/reports/next_due.html"

    def get_queryset(self):
        return super().get_queryset().filter(
            due_date__lte=end_of_day(timezone.now())
        ).exclude(due_date=None)

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or _("due-and-overdue-report")), report_format)


class TestDataReport(BaseReport):

    report_type = "test_data"
    name = "Test Instance Values"
    filter_class = filters.TestDataFilter
    description = mark_safe(_l("This report shows QC test values for select units"))

    category = _l("General")

    MAX_TIS = getattr(settings, "REPORT_TESTDATAREPORT_MAX_TIS", 365 * 3)

    template = "reports/reports/test_data.html"
    formats = [CSV, XLS]

    def filter_form_valid(self, filter_form):

        ntis = self.filter_set.qs.count()
        if ntis > self.MAX_TIS:
            msg = _(
                "This report can only be generated with %(max_num_test_instances)d or fewer Test "
                "Instances.  Your filters are including %(num_test_instances)d. Please reduce the "
                "number of Tests, Sites, Units, or Work Completed time period."
            ) % {
                'max_num_test_instances': self.MAX_TIS,
                'num_test_instances': ntis
            }
            filter_form.add_error("__all__", msg)

        return filter_form.is_valid()

    def get_queryset(self):
        return models.TestInstance.objects.order_by("work_completed")

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or _("test-instance-values-report")), report_format)

    def get_unit_test_info__test_details(self, val):
        return (
            _("Test"),
            ', '.join(models.Test.objects.filter(pk__in=val).order_by("name").values_list("name", flat=True)),
        )

    def get_context(self):

        context = super().get_context()
        context['qs'] = self.filter_set.qs

        qs = self.filter_set.qs.values(
            "test_list_instance__work_completed",
            "unit_test_info__test__name",
            "unit_test_info__test__display_name",
            "unit_test_info__test__type",
            "unit_test_info__unit__name",
            "unit_test_info__unit__site__name",
            "value",
            "string_value",
            "skipped",
            "created_by__username",
        )
        df = pd.DataFrame.from_records(qs)
        context['df'] = df

        return context

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        if self.filter_set.organization == "one_per_row":
            test_data = self.organize_one_per_row(context)
        elif self.filter_set.organization == "group_by_unit_test_date":
            test_data = self.organize_by_unit_test_date(context)

        rows.extend(test_data)
        return rows

    def organize_one_per_row(self, context):

        qs = context['qs'].select_related(
            "test_list_instance",
            "unit_test_info__test",
            "unit_test_info__unit",
            "unit_test_info__unit__site",
            "reference",
            "tolerance",
            "created_by",
        )

        headers = [[
            _("Work Completed"),
            _("Test"),
            _("Unit"),
            _("Site"),
            _("Value"),
            _("Reference"),
            _("Tolerance"),
            _("Skipped"),
            _("Performed By"),
            _("Comment"),
        ]]

        table = headers
        for ti in qs:

            uti = ti.unit_test_info

            table.append([
                ti.test_list_instance.work_completed,
                uti.test.name,
                uti.unit.name,
                uti.unit.site.name if uti.unit.site else "",
                ti.value_display(),
                ti.reference.value_display() if ti.reference else "",
                ti.tolerance.name if ti.tolerance else "",
                ti.skipped,
                format_user(ti.created_by),
                ti.comment,
            ])

        return table

    def organize_by_unit_test_date(self, context):

        qs = context['qs']
        unit_test_combos = list(qs.values_list(
            "unit_test_info__unit",
            "unit_test_info__test",
        ).order_by(
            "unit_test_info__unit__%s" % settings.ORDER_UNITS_BY,
            "unit_test_info__test__display_name",
        ).distinct())

        unique_dates = list(qs.order_by(
            "test_list_instance__work_completed",
        ).values_list(
            "test_list_instance__work_completed",
            flat=True,
        ))

        cells_per_ti = 5
        date_rows = {d: i for i, d in enumerate(unique_dates)}
        ut_cols = {ut: i * cells_per_ti for i, ut in enumerate(unit_test_combos)}

        tests = dict(qs.values_list("unit_test_info__test_id", "unit_test_info__test__display_name").distinct())

        unit_qs = qs.values_list(
            "unit_test_info__unit_id",
            "unit_test_info__unit__site__name",
            "unit_test_info__unit__name",
        ).distinct()
        units = {}
        for unit_id, site_name, unit_name in unit_qs:
            units[unit_id] = "%s : %s" % (site_name or _("Other"), unit_name)

        table = [[_("Date")]]

        for unit_id, test_id in unit_test_combos:
            table[-1].append("%s - %s" % (units[unit_id], tests[test_id]))
            table[-1].append(_("Reference"))
            table[-1].append(_("Tolerance"))
            table[-1].append(_("Peformed By"))
            table[-1].append(_("Comment"))

        ncombos = len(unit_test_combos)
        table += [[ut] + [""] * (cells_per_ti * ncombos) for ut in unique_dates]

        wc_cache = dict(qs.values_list("pk", "test_list_instance__work_completed"))
        for unit_id, test_id in unit_test_combos:

            tis = qs.filter(
                unit_test_info__unit_id=unit_id, unit_test_info__test_id=test_id,
            ).select_related(
                "unit_test_info__test",
                "reference",
                "tolerance",
                "created_by",
            )
            for ti in tis:
                val = ti.value_display(coerce_numerical=False)
                ref = ti.reference.value_display() if ti.reference else ''
                tol = ti.tolerance.name if ti.tolerance else ''
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 1] = val
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 2] = ref
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 3] = tol
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 4] = format_user(ti.created_by)
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 5] = ti.comment

        return table


REPORT_TYPES = [ReportClass for name, ReportClass in REPORT_REGISTRY.items() if name != "BaseReport"]
REPORT_DESCRIPTIONS = {r.report_type: mark_safe(r.description) for r in REPORT_TYPES}
REPORT_TYPE_LOOKUP = {r.report_type: r for r in REPORT_TYPES}
REPORT_CATEGORIES = list(sorted(set([rt.category for rt in REPORT_TYPES])))
REPORT_TYPE_CHOICES = [(c, [(rt.report_type, rt.name) for rt in REPORT_TYPES if rt.category == c]) for c in REPORT_CATEGORIES]  # noqa: E501
