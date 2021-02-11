from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.reports import filters
from qatrack.reports.reports import BaseReport
from qatrack.service_log import models
from qatrack.units import models as umodels


class ScheduledTemplatesReport(filters.ServiceEventScheduleFilterDetailsMixin, BaseReport):

    report_type = "scheduled-templates-summary"
    name = _l("Service Event Template Assignment Summary")
    filter_class = filters.ScheduledServiceEventFilter
    description = mark_safe(_l(
        "This report includes a summary of all service event templates assigned to "
        "selected sites, units, frequencies, and groups."
    ))
    category = _l("Service Log")

    template = "reports/service_log/assigned_templates.html"

    def get_queryset(self):
        return models.ServiceEventSchedule.objects.all()

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "template-assignment-summary-report"), report_format)

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

            for schedule in self.get_schedules_for_site(self.filter_set.qs, site):
                sites_data[-1][-1].append({
                    'unit_name': schedule.unit_service_area.unit.name,
                    'service_area_name': schedule.unit_service_area.service_area.name,
                    'frequency': schedule.frequency.name if schedule.frequency else _("Ad Hoc"),
                    'service_event_template_name': schedule.service_event_template.name,
                    'assigned_to': schedule.assigned_to.name,
                    'link': self.make_url(schedule.get_absolute_url(), plain=True),
                })

        context['sites_data'] = sites_data

        return context

    def get_schedules_for_site(self, qs, site):
        """Get Schedules from filtered queryset for input site"""

        schedules = qs.filter(unit_service_area__unit__site=site)

        schedules = schedules.order_by(
            "unit_service_area__unit__%s" % settings.ORDER_UNITS_BY,
            "unit_service_area__service_area__name",
            "service_event_template__name",
        ).select_related(
            "assigned_to",
            "frequency",
            "unit_service_area",
            "unit_service_area__unit__site",
            "unit_service_area__unit",
            "unit_service_area__service_area",
            "service_event_template",
        )

        return schedules

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        rows.append([
            _("Site"),
            _("Unit"),
            _("Service Area"),
            _("Template Name"),
            _("Frequency"),
            _("Assigned To"),
            _("Link"),
        ])

        for site, utcs in context['sites_data']:
            for utc in utcs:
                rows.append([
                    site,
                    utc['unit_name'],
                    utc['service_area_name'],
                    utc['service_event_template_name'],
                    utc['frequency'],
                    utc['assigned_to'],
                    utc['link'],
                ])

        return rows
