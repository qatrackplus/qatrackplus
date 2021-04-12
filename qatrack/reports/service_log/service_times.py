from collections import defaultdict

from django.conf import settings
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa.templatetags.qa_tags import hour_min
from qatrack.qatrack_core.utils import relative_dates
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport
from qatrack.reports.service_log.summary import ServiceEventReportMixin
from qatrack.service_log import models
from qatrack.units import models as umodels


class ServiceTimesReport(ServiceEventReportMixin, BaseReport):

    report_type = "service-times"
    name = _l("Service Times")
    filter_class = filters.ServiceEventDetailsFilter
    description = mark_safe(_l(
        "This report summarizes the service times, including lost time, "
        "for service events on all selected units."
    ))

    category = _l("Service Log")

    template = "reports/service_log/service_times.html"

    MAX_SES = 10000

    def get_queryset(self):
        return models.ServiceEvent.objects.all()

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "service-times"), report_format)

    def get_context(self):

        context = super().get_context()

        # since we're grouping by site, we need to handle sites separately
        sites = self.filter_set.qs.order_by(
            "unit_service_area__unit__site__name",
        ).values_list(
            "unit_service_area__unit__site",
            flat=True,
        ).distinct()

        units = (
            models.Unit.objects.filter(pk__in=self.filter_set.form.cleaned_data.get("unit_service_area__unit")) or
            models.Unit.objects.all()
        ).select_related(
            "site",
        )

        all_service_types = models.ServiceType.objects.all()
        service_types = self.filter_set.form.cleaned_data.get("service_type") or all_service_types

        all_service_areas = models.ServiceArea.objects.all()
        service_areas = self.filter_set.form.cleaned_data.get("unit_service_area__service_area") or all_service_areas

        # if the service events are filtered by service type/ service area the uptime
        # calculation won't make sense
        self.calc_uptime = (
            len(service_areas) == len(all_service_areas) and
            len(service_types) == len(all_service_types)
        )

        start_date, end_date = relative_dates(
            self.filter_set.form.cleaned_data.get('datetime_service', 'Last 365 Days')
        ).range()

        sites_data = []

        for site in sites:

            if site:  # site can be None here since not all units may have a site
                site = umodels.Site.objects.get(pk=site)

            sites_data.append((site.name if site else "", []))

            ses = self.get_ses_for_site(self.filter_set.qs, site)
            unit_ses = defaultdict(list)
            for se in ses:
                unit_ses[se.unit_service_area.unit_id].append(se)

            for unit in units.filter(site=site):

                available = timezone.timedelta(hours=unit.get_potential_time(start_date.date(), end_date.date()))
                total_lost_time = timezone.timedelta()
                total_service_time = timezone.timedelta()
                total_events = 0

                service_type_info = {}
                for st in service_types:
                    service_type_info[st.pk] = {
                        'name': st.name,
                        'n_service_events': 0,
                        'service_time': timezone.timedelta(),
                        'lost_time': timezone.timedelta(),
                    }

                for se in unit_ses[unit.id]:

                    service_type_info[se.service_type_id]['n_service_events'] += 1
                    total_events += 1

                    st = se.duration_service_time or timezone.timedelta()
                    service_type_info[se.service_type_id]['service_time'] += st
                    total_service_time += st

                    lt = se.duration_lost_time or timezone.timedelta()
                    service_type_info[se.service_type_id]['lost_time'] += lt
                    total_lost_time += lt

                for st in service_types:
                    service_type_info[st.pk]['service_time'] = hour_min(service_type_info[st.pk]['service_time'])
                    downtime = 100 * service_type_info[st.pk]['lost_time'] / available if available else 100
                    service_type_info[st.pk]['downtime'] = downtime
                    service_type_info[st.pk]['lost_time'] = hour_min(service_type_info[st.pk]['lost_time'])

                uptime = None
                if self.calc_uptime:
                    uptime = 100 * (available - total_lost_time) / available if available else 0

                sites_data[-1][-1].append({
                    'unit': unit.name,
                    'n_service_events': total_events,
                    'service_time': hour_min(total_service_time),
                    'lost_time': hour_min(total_lost_time),
                    'available_time': hour_min(available),
                    'uptime': uptime,
                    'downtime': 100 * total_lost_time / available if available else 0,
                    'service_types': list(service_type_info.values()),
                })

        context['sites_data'] = sites_data
        context['n_service_types'] = len(service_types)

        return context

    def get_ses_for_site(self, qs, site):
        """Get Test List Instances from filtered queryset for input site"""

        ses = qs.filter(unit_service_area__unit__site=site)

        ses = ses.order_by(
            "unit_service_area__unit__%s" % settings.ORDER_UNITS_BY,
        ).select_related(
            "unit_service_area",
            "service_type",
        )

        return ses

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        header = [
            _("Site"),
            _("Unit"),
            _("Service Type"),
            _("# of Service Events"),
            _("Service Time (HH:MM)"),
            _("Lost Time (HH:MM)"),
            _("Down Time (%)"),
            _("Available Time (HH:MM)"),
            _("Uptime (%)"),
        ]

        rows.append(header)

        for site, unit_infos in context['sites_data']:
            for unit_info in unit_infos:

                for st_idx, service_type in enumerate(unit_info['service_types']):
                    first = st_idx == 0

                    row = [
                        site if first else "",
                        unit_info['unit'] if first else "",
                        service_type['name'],
                        service_type['n_service_events'],
                        service_type['service_time'],
                        service_type['lost_time'],
                        service_type['downtime'],
                        unit_info['available_time'] if first else "",
                        unit_info['uptime'] if first and self.calc_uptime else "",
                    ]

                    rows.append(row)

                rows.append([
                    "",
                    "",
                    _("Totals:"),
                    unit_info['n_service_events'],
                    unit_info['service_time'],
                    unit_info['lost_time'],
                    unit_info['downtime'],
                ])

        return rows
