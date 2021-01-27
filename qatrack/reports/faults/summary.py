from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.faults import models
from qatrack.qatrack_core.dates import format_datetime
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport
from qatrack.units import models as umodels


class FaultReportMixin:

    category = _l("Faults")

    def get_queryset(self):
        return models.Fault.objects.select_related(
            "fault_type",
            "unit",
            "unit__site",
            "created_by",
            "modified_by",
            "reviewed_by",
            "modality",
            "treatment_technique",
        ).prefetch_related(
            "related_service_events",
        )

    def filter_form_valid(self, filter_form):

        nfaults = self.filter_set.qs.count()
        if nfaults > self.MAX_FAULTS:
            filter_form.add_error(
                "__all__", "This report can only be generated with %d or fewer Faults"
                " Your filters are including %d. Please reduce the "
                "number of Faults." % (self.MAX_FAULTS, nfaults)
            )

        return filter_form.is_valid()

    def get_unit_details(self, val):
        units = umodels.Unit.objects.filter(pk__in=val).select_related("site")
        return (
            "Unit(s)", ', '.join("%s%s" % ("%s - " % unit.site.name if unit.site else "", unit.name) for unit in units)
        )

    def get_unit__site_details(self, sites):
        return ("Site(s)", (', '.join(s.name if s != 'null' else _("Other") for s in sites)).strip(", "))

    def get_review_status_details(self, val):
        return (_("Review Status"), dict(self.filter_set.form.fields['review_status'].choices)[val] if val else "")

    def get_faults_for_site(self, qs, site):
        """Get Test List Instances from filtered queryset for input site"""

        faults = qs.filter(unit__site=site)

        faults = faults.order_by(
            "unit__%s" % settings.ORDER_UNITS_BY,
            "occurred",
        ).select_related(
            "fault_type",
            "created_by",
            "modified_by",
            "reviewed_by",
        ).prefetch_related(
            "related_service_events",
        )

        return faults


class FaultSummaryReport(FaultReportMixin, BaseReport):

    report_type = "fault_summary"
    name = _l("Fault Summary")
    filter_class = filters.FaultSummaryFilter
    description = mark_safe(_l(
        "This report includes a summary of all faults from a given time period for selected units"
    ))

    template = "reports/faults/summary.html"

    MAX_FAULTS = 300

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "faults-summary"), report_format)

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
                sites_data[-1][-1].append({
                    'id': fault.id,
                    'fault_type': fault.fault_type.code,
                    'unit_name': fault.unit.name,
                    'modality': fault.modality.name if fault.modality else _("Not specified"),
                    'treatment_technique': (
                        fault.treatment_technique.name if fault.treatment_technique else _("Not specified")
                    ),
                    'occurred': format_datetime(fault.occurred),
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
            _("Link"),
        ]

        rows.append(header)

        for site, faults in context['sites_data']:
            for fault in faults:
                row = [
                    fault['id'],
                    fault['occurred'],
                    site,
                    fault['unit_name'],
                    fault['fault_type'],
                    fault['modality'],
                    fault['treatment_technique'],
                    fault['link'],
                ]

                rows.append(row)

        return rows
