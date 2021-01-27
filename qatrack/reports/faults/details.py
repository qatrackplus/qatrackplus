from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django_comments.models import Comment

from qatrack.qatrack_core.dates import format_datetime
from qatrack.reports import filters
from qatrack.reports.faults.summary import FaultReportMixin
from qatrack.reports.reports import BaseReport, format_user
from qatrack.units import models as umodels


class FaultDetailsReport(FaultReportMixin, BaseReport):

    report_type = "fault_details"
    name = _l("Fault Details")
    filter_class = filters.FaultDetailsFilter
    description = mark_safe(
        _l(
            "This report includes details of all Faults from a given"
            "time period for selected units"
        )
    )

    template = "reports/faults/details.html"

    MAX_FAULTS = 200

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "fault-details"), report_format)

    def get_context(self):

        context = super().get_context()

        # since we're grouping by site, we need to handle sites separately
        form = self.get_filter_form()
        reviewed = form.cleaned_data.get("review_status")
        qs = self.filter_set.qs
        if reviewed == "unreviewed":
            qs = qs.filter(reviewed_by=None)
        elif reviewed == "reviewed":
            qs = qs.exclude(reviewed_by=None)

        sites = qs.order_by(
            "unit__site__name",
        ).values_list(
            "unit__site",
            flat=True,
        ).distinct()

        sites_data = []

        for site in sites:

            if site:  # site can be None here since not all units may have a site
                site = umodels.Site.objects.get(pk=site)

            sites_data.append((site.name if site else "", []))

            for fault in self.get_faults_for_site(qs, site):
                related_ses = []
                for se_rel in fault.related_service_events.all():
                    related_ses.append(
                        (se_rel.id, se_rel.datetime_service, self.make_url(se_rel.get_absolute_url(), plain=True))
                    )

                comments = []
                comment_qs = Comment.objects.for_model(fault).values_list(
                    "user__username",
                    "submit_date",
                    "comment",
                )
                for user, dt, comment in comment_qs:
                    comments.append((user, format_datetime(dt), comment))

                sites_data[-1][-1].append({
                    'id': fault.id,
                    'occurred': format_datetime(fault.occurred),
                    'site': site.name if site else "",
                    'unit_name': fault.unit.name,
                    'fault_type': fault.fault_type.code,
                    'modality': fault.modality.name if fault.modality else _("Not specified"),
                    'treatment_technique': (
                        fault.treatment_technique.name if fault.treatment_technique else _("Not specified")
                    ),
                    'created_by': format_user(fault.created_by),
                    'created': format_datetime(fault.created),
                    'modified_by': format_user(fault.modified_by),
                    'modified': format_datetime(fault.modified),
                    'reviewed_by': format_user(fault.reviewed_by),
                    'reviewed': format_datetime(fault.reviewed),
                    'related_ses': related_ses,
                    'comments': comments,
                    'link': self.make_url(fault.get_absolute_url(), plain=True),
                })

        context['sites_data'] = sites_data

        return context

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        header = [
            _("Fault ID"),
            _("Occurred"),
            _("Site"),
            _("Unit"),
            _("Fault Type"),
            _("Modality"),
            _("Treatment Technique"),
            _("Created By"),
            _("Created Date"),
            _("Modified By"),
            _("Modified Date"),
            _("Reviewed By"),
            _("Reviewed Date"),
            _("Related Service Events"),
            _("Link"),
        ]

        rows.append(header)

        for site, faults in context['sites_data']:
            for fault in faults:

                related = ','.join(link for __, __, link in fault['related_ses'])

                comments = []
                for comment in fault['comments']:
                    comments.append("%s,%s,%s" % comment)
                comments = '\n'.join(comments)

                row = [
                    fault['id'],
                    fault['occurred'],
                    site,
                    fault['unit_name'],
                    fault['fault_type'],
                    fault['modality'],
                    fault['treatment_technique'],
                    fault['created_by'].split("(")[0],
                    fault['created'],
                    fault['modified_by'].split("(")[0],
                    fault['modified'],
                    fault['reviewed_by'].split("(")[0],
                    fault['reviewed'],
                    related,
                    comments,
                    fault['link'],
                ]

                rows.append(row)

        return rows
