from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa import models
from qatrack.reports import filters
from qatrack.reports.reports import BaseReport
from qatrack.units import models as umodels


class AssignedQCReport(filters.UnitTestCollectionFilterDetailsMixin, BaseReport):

    report_type = "qc-assignment-summary"
    name = _l("QC Assignment Summary")
    filter_class = filters.UnitTestCollectionFilter
    description = mark_safe(_l(
        "This report includes a summary of all Test Lists (Cycles) assigned to "
        "selected sites, units, frequencies, and groups."
    ))
    category = _l("QC")

    template = "reports/qc/assigned_qc.html"

    def get_queryset(self):
        return models.UnitTestCollection.objects.all()

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "qc-assignment-summary-report"), report_format)

    def get_context(self):

        context = super().get_context()

        # since we're grouping by site, we need to handle sites separately
        sites = self.filter_set.qs.order_by(
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

            for utc in self.get_utcs_for_site(self.filter_set.qs, site):
                sites_data[-1][-1].append({
                    'unit_name': utc.unit.name,
                    'frequency': utc.frequency.name if utc.frequency else _("Ad Hoc"),
                    'name': utc.name,
                    'assigned_to': utc.assigned_to.name,
                    'link': self.make_url(utc.get_absolute_url(), plain=True),
                })

        context['sites_data'] = sites_data

        return context

    def get_utcs_for_site(self, qs, site):
        """Get Test List Instances from filtered queryset for input site"""

        utcs = qs.filter(unit__site=site)

        utcs = utcs.order_by(
            "unit__%s" % settings.ORDER_UNITS_BY,
            "name",
        ).select_related(
            "assigned_to",
            "frequency",
            "unit",
            "unit__site",
        )

        return utcs

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        rows.append([
            _("Site"),
            _("Unit"),
            _("Test list (Cycle)"),
            _("Frequency"),
            _("Assigned To"),
            _("Link"),
        ])

        for site, utcs in context['sites_data']:
            for utc in utcs:
                rows.append([
                    site,
                    utc['unit_name'],
                    utc['name'],
                    utc['frequency'],
                    utc['assigned_to'],
                    utc['link'],
                ])

        return rows


class AssignedQCDetailsReport(filters.UnitTestCollectionFilterDetailsMixin, BaseReport):

    report_type = "qc-assignment-details"
    name = _l("QC Assignment Details")
    filter_class = filters.UnitTestCollectionFilter
    description = mark_safe(_l(
        "This report includes details of all Test Lists (Cycles) assigned to "
        "selected sites, units, frequencies, and groups."
    ))
    category = _l("QC")

    template = "reports/qc/assigned_qc_details.html"

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or "qc-assignment-details-report"), report_format)

    def get_context(self):

        context = super().get_context()

        # since we're grouping by site, we need to handle sites separately
        sites = self.filter_set.qs.order_by(
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

            for utc in self.get_utcs_for_site(self.filter_set.qs, site):

                all_lists = utc.tests_object.test_list_members().prefetch_related("testlistmembership_set__test",)
                for li in all_lists:
                    li.all_tests = li.ordered_tests()

                for li in all_lists:
                    utis = models.UnitTestInfo.objects.filter(
                        test__in=li.all_tests,
                        unit=utc.unit,
                    ).select_related("test", "test__category", "reference", "tolerance")

                    li.utis = list(sorted(utis, key=lambda uti: li.all_tests.index(uti.test)))

                sites_data[-1][-1].append({
                    'unit_name': utc.unit.name,
                    'visible_to': ', '.join(g.name for g in utc.visible_to.order_by('name')),
                    'all_lists': all_lists,
                    'is_cycle': len(all_lists) > 1,
                    'frequency': utc.frequency.name if utc.frequency else _("Ad Hoc"),
                    'name': utc.name,
                    'assigned_to': utc.assigned_to.name,
                    'link': self.make_url(utc.get_absolute_url(), plain=True),
                })

        context['sites_data'] = sites_data

        return context

    def get_utcs_for_site(self, qs, site):
        """Get Test List Instances from filtered queryset for input site"""

        utcs = qs.filter(unit__site=site)

        utcs = utcs.order_by(
            "unit__%s" % settings.ORDER_UNITS_BY,
            "name",
        ).select_related(
            "assigned_to",
            "frequency",
            "unit",
            "unit__site",
        )

        return utcs

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        rows.append([
            _("Site"),
            _("Unit"),
            _("Test list (Cycle)"),
            _("Frequency"),
            _("Assigned To"),
            _("Link"),
        ])

        for site, utcs in context['sites_data']:
            for utc in utcs:
                rows.append([
                    site,
                    utc['unit_name'],
                    utc['name'],
                    utc['frequency'],
                    utc['assigned_to'],
                    utc['link'],
                ])

        return rows
