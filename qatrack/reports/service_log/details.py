from collections import defaultdict

from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qatrack_core.utils import format_as_date, format_datetime
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport, format_user
from qatrack.reports.service_log.summary import ServiceEventReportMixin
from qatrack.units import models as umodels


class ServiceEventDetailsReport(ServiceEventReportMixin, BaseReport):

    report_type = "service_event_details"
    name = _l("Service Event Details")
    filter_class = filters.ServiceEventDetailsFilter
    description = mark_safe(
        _l(
            "This report includes details of all Service Events from a given"
            "time period for selected units"
        )
    )

    template = "reports/service_log/details.html"

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "service-event-details"), report_format)

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
                initiated_by_link = (
                    se.test_list_instance_initiated_by.get_absolute_url()
                    if se.test_list_instance_initiated_by else None
                )

                related_ses = []
                for se_rel in se.service_event_related.all():
                    related_ses.append(
                        (se_rel.id, se_rel.datetime_service, self.make_url(se_rel.get_absolute_url(), plain=True))
                    )

                group_linkers = defaultdict(list)
                for gli in se.grouplinkerinstance_set.order_by("group_linker__name", "user__username"):
                    group_linkers[gli.group_linker.name].append(gli.user.username)

                hours = []
                for h in se.hours_set.order_by("-time"):
                    u = h.user.username if h.user else "%s (%s)" % (h.third_party.name, h.third_party.vendor.name)
                    hours.append((u, h.time))

                rts_qc = []
                for rts in se.returntoserviceqa_set.order_by("unit_test_collection__name"):
                    tli = rts.test_list_instance
                    wc = format_datetime(tli.work_completed) if tli else ""
                    link = self.make_url(tli.get_absolute_url(), plain=True) if tli else ""
                    rts_qc.append((rts.unit_test_collection.name, wc, link))

                parts = []
                if settings.USE_PARTS:
                    for part_used in se.partused_set.order_by("part__name"):
                        parts.append((part_used.part.name, str(part_used.from_storage or ""), part_used.quantity))

                attachments = []
                for a in se.attachment_set.all():
                    attachments.append((a.label, a.attachment.url))

                sites_data[-1][-1].append({
                    'created_by': format_user(se.user_created_by),
                    'problem': se.problem_description,
                    'work': se.work_description,
                    'safety': se.safety_precautions,
                    'unit_name': se.unit_service_area.unit.name,
                    'service_area': se.unit_service_area.service_area.name,
                    'service_type': se.service_type.name,
                    'status': se.service_status.name,
                    'service_date': format_as_date(se.datetime_service),
                    'service_time': se.duration_service_time,
                    'lost_time': se.duration_lost_time,
                    'link': self.make_url(se.get_absolute_url(), plain=True),
                    'initiated_by': se.test_list_instance_initiated_by,
                    'initiated_by_link': initiated_by_link,
                    'related_ses': related_ses,
                    'group_linkers': sorted(group_linkers.items()),
                    'hours': hours,
                    'rts_qc': rts_qc,
                    'parts': parts,
                    'attachments': attachments,
                })

        context['sites_data'] = sites_data
        context['use_parts'] = settings.USE_PARTS

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
                ]

                if context['include_description']:
                    row.extend([
                        se['problem'],
                        se['work'],
                    ])

                row.append(se['link'])
                rows.append(row)

        return rows
