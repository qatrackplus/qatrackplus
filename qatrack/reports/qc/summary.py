from django.conf import settings
from django.db.models import Q
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa import models
from qatrack.qatrack_core.utils import format_as_date
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport
from qatrack.units import models as umodels


class QCSummaryReport(BaseReport):

    report_type = "qc-summary-by-date"
    name = _l("QC Summary")
    filter_class = filters.TestListInstanceFilter
    description = mark_safe(_l(
        "This report lists all Test List Instances from a given time period for "
        "selected sites, units, frequencies, and groups."
    ))

    MAX_TLIS = getattr(settings, "REPORT_QCSUMMARYREPORT_MAX_TLIS", 5000)

    template = "reports/qc/qc_summary.html"

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
