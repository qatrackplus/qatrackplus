from collections import defaultdict

from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django_comments.models import Comment

from qatrack.qatrack_core.dates import format_as_date, format_datetime
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

    MAX_SES = 100

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
                    self.make_url(se.test_list_instance_initiated_by.get_absolute_url(), plain=True)
                    if se.test_list_instance_initiated_by else None
                )

                related_ses = []
                for se_rel in se.service_event_related.all():
                    related_ses.append(
                        (se_rel.id, se_rel.datetime_service, self.make_url(se_rel.get_absolute_url(), plain=True))
                    )

                group_linkers = defaultdict(list)
                for gli in se.grouplinkerinstance_set.all():
                    group_linkers[gli.group_linker.name].append(gli.user.username)

                hours = []
                for h in se.hours_set.all():
                    u = h.user.username if h.user else "%s (%s)" % (str(h.third_party), h.third_party.vendor.name)
                    hours.append((u, h.time))

                rts_qc = []
                for rts in se.returntoserviceqa_set.all():
                    tli = rts.test_list_instance
                    wc = format_datetime(tli.work_completed) if tli else ""
                    link = self.make_url(tli.get_absolute_url(), plain=True) if tli else ""
                    rts_qc.append((rts.unit_test_collection.name, wc, link))

                rts_comments = []
                comment_qs = Comment.objects.for_model(se).values_list(
                    "user__username",
                    "submit_date",
                    "comment",
                )
                for user, dt, comment in comment_qs:
                    rts_comments.append((user, format_datetime(dt), comment))

                parts = []
                for part_used in se.partused_set.all():
                    parts.append((part_used.part.name, str(part_used.from_storage or ""), part_used.quantity))

                attachments = []
                for a in se.attachment_set.all():
                    attachments.append((a.label, self.make_url(a.attachment.url, plain=True)))

                sites_data[-1][-1].append({
                    'id': se.id,
                    'service_date': format_as_date(se.datetime_service),
                    'site': site.name if site else "",
                    'unit_name': se.unit_service_area.unit.name,
                    'service_area': se.unit_service_area.service_area.name,
                    'service_type': se.service_type.name,
                    'service_time': se.duration_service_time,
                    'lost_time': se.duration_lost_time,
                    'status': se.service_status.name,
                    'created_by': format_user(se.user_created_by),
                    'created_date': format_datetime(se.datetime_created),
                    'modified_by': format_user(se.user_modified_by),
                    'modified_date': format_datetime(se.datetime_modified),
                    'problem': se.problem_description,
                    'work': se.work_description,
                    'safety': se.safety_precautions,
                    'initiated_by': se.test_list_instance_initiated_by,
                    'initiated_by_link': initiated_by_link,
                    'related_ses': related_ses,
                    'group_linkers': sorted(group_linkers.items()),
                    'hours': hours,
                    'rts_qc': rts_qc,
                    'rts_comments': rts_comments,
                    'parts': parts,
                    'attachments': attachments,
                    'link': self.make_url(se.get_absolute_url(), plain=True),
                })

        context['sites_data'] = sites_data

        return context

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        header = [
            _("Service Event ID"),
            _("Service Date"),
            _("Site"),
            _("Unit"),
            _("Service Area"),
            _("Service Type"),
            _("Service Time"),
            _("Lost Time"),
            _("Status"),
            _("Created By"),
            _("Created Date"),
            _("Modified By"),
            _("Modified Date"),
            _("Problem Description"),
            _("Work Description"),
            _("Safety Precautions"),
            _("Initiated By"),
            _("Related Service Events"),
            _("Group Members Involved"),
            _("Work Durations"),
            _("Return To Service QC"),
            _("Return To Service Comments"),
            _("Parts Used"),
            _("Attachments"),
            _("Link"),
        ]

        rows.append(header)

        for site, ses in context['sites_data']:
            for se in ses:

                related = ','.join(link for __, __, link in se['related_ses'])

                initiated_by = se['initiated_by_link']

                group_members = []
                for group, members in se['group_linkers']:
                    group_members.append("%s=%s" % (group, ','.join(m.split("(")[0] for m in members)))
                group_members = "\n".join(group_members)

                hours = ','.join("%s=%s" % ut for ut in se['hours'])

                rts_qc = []
                for utc, wc, link in se['rts_qc']:
                    rts_qc.append("%s,%s,%s" % (utc, wc or _("Not completed"), link or _("Not completed")))
                rts_qc = '\n'.join(rts_qc)

                rts_comments = []
                for comments in se['rts_comments']:
                    rts_comments.append("%s,%s,%s" % comments)
                rts_comments = '\n'.join(rts_comments)

                parts = ','.join("%s=%s=%s" % p for p in se['parts'])

                attachments = ','.join(link for __, link in se['attachments'])

                row = [
                    se['id'],
                    se['service_date'],
                    site,
                    se['unit_name'],
                    se['service_area'],
                    se['service_type'],
                    se['service_time'],
                    se['lost_time'],
                    se['status'],
                    se['created_by'].split("(")[0],
                    se['created_date'],
                    se['modified_by'].split("(")[0],
                    se['modified_date'],
                    se['problem'],
                    se['work'],
                    se['safety'],
                    initiated_by,
                    related,
                    group_members,
                    hours,
                    rts_qc,
                    rts_comments,
                    parts,
                    attachments,
                    se['link'],
                ]

                rows.append(row)

        return rows
