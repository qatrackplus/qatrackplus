from django.conf import settings
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa import models
from qatrack.qatrack_core.dates import end_of_day, format_as_date
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport
from qatrack.units import models as umodels


class DueDatesReportMixin(filters.UnitTestCollectionFilterDetailsMixin):

    category = _l("QC")

    def get_queryset(self):
        qs = models.UnitTestCollection.objects.select_related(
            "assigned_to",
            "unit",
            "frequency",
        )
        return qs

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
                [site],
                [_("Unit"),
                 _("Name"),
                 _("Frequency"),
                 _("Due Date"),
                 _("Window"),
                 _("Assigned To"),
                 _("Perform")],
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
    name = _l("Next Due Dates for QC")
    filter_class = filters.UnitTestCollectionSchedulingFilter
    description = mark_safe(_l("This report shows QC tests whose next due date fall in the selected time period."))

    category = _l("Scheduling")
    template = "reports/qc/next_due.html"

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or _("next-due-dates-report")), report_format)


class DueAndOverdueQCReport(DueDatesReportMixin, BaseReport):

    report_type = "due_and_overdue"
    name = _l("Due and Overdue QC")
    filter_class = filters.UnitTestCollectionFilter
    description = mark_safe(_l("This report shows QC tests which are currently due or overdue"))

    category = _l("Scheduling")
    template = "reports/qc/next_due.html"

    def get_queryset(self):
        return super().get_queryset().filter(due_date__lte=end_of_day(timezone.now())).exclude(due_date=None)

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or _("due-and-overdue-report")), report_format)
