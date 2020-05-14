from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qatrack_core.utils import format_as_date, format_timedelta
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport
from qatrack.service_log import models
from qatrack.units import models as umodels


class BaseServiceEventReport(BaseReport):

    def get_queryset(self):
        return models.ServiceEvent.objects.select_related(
            "unit_service_area__unit",
            "unit_service_area__unit__site",
        )

    def get_unit_service_area__unit_details(self, val):
        units = umodels.Unit.objects.filter(pk__in=val).select_related("site")
        return (
            "Site/Units",
            ', '.join("%s%s" % ("%s - " % unit.site.name if unit.site else "", unit.name) for unit in units)
        )

    def get_unit_service_area__unit__site_details(self, sites):
        return ("Sites", (', '.join(s.name if s != 'null' else "" for s in sites)).strip(", "))

    def get_ses_for_site(self, qs, site):
        """Get Test List Instances from filtered queryset for input site"""

        ses = qs.filter(unit_service_area__unit__site=site)

        ses = ses.order_by(
            "unit_service_area__unit__%s" % settings.ORDER_UNITS_BY,
            "datetime_service",
        ).select_related(
            "service_status",
            "unit_service_area",
            "unit_service_area__unit",
            "unit_service_area__service_area",
        )

        return ses


class ServiceEventSummaryReport(BaseServiceEventReport):

    report_type = "service_event_summary"
    name = "Service Event Summary"
    filter_class = filters.ServiceEventFilter
    description = mark_safe(
        _l(
            "This report includes a summary of all Service Events from a given"
            "time period for selected units"
        )
    )
    category = _l("Service Log")

    template = "reports/service_log/summary.html"

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "service-event-summary"), report_format)

    def get_include_description_details(self, val):
        return (_("Include Desciption"), [_("No"), _("Yes")][val])

    def get_context(self):

        context = super().get_context()

        # since we're grouping by site, we need to handle sites separately
        sites = self.filter_set.qs.order_by(
            "unit_service_area__unit__site__name",
        ).values_list(
            "unit_service_area__unit__site",
            flat=True,
        ).distinct()

        sites_data = []

        for site in sites:

            if site:  # site can be None here since not all units may have a site
                site = umodels.Site.objects.get(pk=site)

            sites_data.append((site.name if site else "", []))

            for se in self.get_ses_for_site(self.filter_set.qs, site):
                sites_data[-1][-1].append({
                    'problem': se.problem_description,
                    'work': se.work_description,
                    'unit_name': se.unit_service_area.unit.name,
                    'service_area': se.unit_service_area.service_area.name,
                    'status': se.service_status.name,
                    'service_date': format_as_date(se.datetime_service),
                    'service_time': format_timedelta(se.duration_service_time),
                    'lost_time': format_timedelta(se.duration_lost_time),
                    'link': self.make_url(se.get_absolute_url(), plain=True),
                })

        context['sites_data'] = sites_data
        context['include_description'] = self.filter_set.form.cleaned_data.get("include_description")

        return context

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        header = [
            _("Service Date"),
            _("Site"),
            _("Unit"),
            _("Service Area"),
            _("Status"),
            _("Service Time"),
            _("Lost Time"),
        ]
        if context['include_description']:
            header.extend([_("Problem Description"), _("Work Description")])

        header.append(_("Link"))

        rows.append(header)

        for site, ses in context['sites_data']:
            for se in ses:
                row = [
                    se['service_date'],
                    site,
                    se['unit_name'],
                    se['service_area'],
                    se['status'],
                    se['service_time'],
                    se['lost_time'],
                    se['link'],
                ]

                if context['include_description']:
                    row.extend([
                        se['problem'],
                        se['work'],
                    ])
                rows.append(row)

        return rows
