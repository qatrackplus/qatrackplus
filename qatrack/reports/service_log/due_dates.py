from django.conf import settings
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qatrack_core.dates import end_of_day, format_as_date
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport
from qatrack.service_log import models
from qatrack.units import models as umodels


class DueDatesReportMixin(filters.ServiceEventScheduleFilterDetailsMixin):

    category = _l("Service Log")

    def get_queryset(self):
        return models.ServiceEventSchedule.objects.select_related(
            "assigned_to",
            "service_event_template",
            "unit_service_area",
            "unit_service_area__unit",
            "unit_service_area__service_area",
            "frequency",
        )

    def get_context(self):

        context = super().get_context()
        qs = self.filter_set.qs

        sites = self.filter_set.qs.order_by("unit_service_area__unit__site__name").values_list(
            "unit_service_area__unit__site", flat=True
        ).distinct()

        sites_data = []

        for site in sites:

            if site:  # site can be None here since not all units may have a site
                site = umodels.Site.objects.get(pk=site)

            sites_data.append((site.name if site else "", []))

            schedules = qs.filter(
                unit_service_area__unit__site_id=(site if site else None),
                due_date__isnull=False,
            ).order_by("due_date", "unit_service_area__unit__%s" % settings.ORDER_UNITS_BY)

            for schedule in schedules:

                window = schedule.window()
                if window:
                    window = "%s - %s" % (format_as_date(window[0]), format_as_date(window[1]))

                sites_data[-1][-1].append({
                    'schedule': schedule,
                    'unit_name': schedule.unit_service_area.unit.name,
                    'service_area_name': schedule.unit_service_area.service_area.name,
                    'service_event_template_name': schedule.service_event_template.name,
                    'window': window,
                    'frequency': schedule.frequency.name if schedule.frequency else _("Ad Hoc"),
                    'due_date': format_as_date(schedule.due_date),
                    'assigned_to': schedule.assigned_to.name,
                    'link': self.make_url(schedule.get_absolute_url(), plain=True),
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
                [
                    _("Unit"),
                    _("Service Area"),
                    _("Template Name"),
                    _("Frequency"),
                    _("Due Date"),
                    _("Window"),
                    _("Assigned To"),
                    _("Perform")
                ],
            ])

            for row in site_rows:
                rows.append([
                    row['unit_name'],
                    row['service_area_name'],
                    row['service_event_template_name'],
                    row['frequency'],
                    format_as_date(row['schedule'].due_date),
                    row['window'],
                    row['assigned_to'],
                ])

        return rows


class NextScheduledServiceEventsDueDatesReport(DueDatesReportMixin, BaseReport):

    report_type = "service_event_next_due"
    name = _l("Next Due Dates for Scheduled Service Events")
    filter_class = filters.SchedulingFilter
    description = mark_safe(
        _l("This report shows scheduled service events whose next due date fall in the selected time period.")
    )

    category = _l("Service Event Scheduling")
    template = "reports/service_log/next_due.html"

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or _("next-due-dates-for-sl-report")), report_format)


class DueAndOverdueServiceEventScheduleReport(DueDatesReportMixin, BaseReport):

    report_type = "service_event_due_and_overdue"
    name = _l("Due and Overdue Scheduled Service Events")
    filter_class = filters.ScheduledServiceEventFilter
    description = mark_safe(_l("This report shows scheduled service events which are currently due or overdue"))

    category = _l("Service Event Scheduling")
    template = "reports/service_log/next_due.html"

    def get_queryset(self):
        return super().get_queryset().filter(due_date__lte=end_of_day(timezone.now())).exclude(due_date=None)

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or _("due-and-overdue-sl-report")), report_format)
