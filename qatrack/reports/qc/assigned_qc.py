from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa import models
from qatrack.reports import filters
from qatrack.reports.reports import PDF, BaseReport
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

    MAX_UTCS = 125

    def filter_form_valid(self, filter_form):

        nutc = self.filter_set.qs.count()
        if nutc > self.MAX_UTCS:
            msg = _(
                "This report can only be generated with %(max_num_unit_assignments)d or fewer Test List "
                "Assignments.  Your filters are including %(num_unit_assignments)d. Please reduce the "
                "number of Sites, Units, Frequencies, or Assigned To Groups."
            ) % {
                'max_num_unit_assignments': self.MAX_UTCS,
                'num_unit_assignments': nutc
            }
            filter_form.add_error("__all__", msg)

        return filter_form.is_valid()

    def get_queryset(self):
        return models.UnitTestCollection.objects.all()

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

        cat_cache = dict(models.Test.objects.values_list("id", "category__name"))
        ref_cache = dict((r.pk, r) for r in models.Reference.objects.all())
        tol_cache = dict((t.pk, t) for t in models.Tolerance.objects.all())

        units = self.filter_set.form.cleaned_data['unit']
        utis = models.UnitTestInfo.objects.all()
        if units:
            utis = utis.filter(unit__in=units)

        uti_cache = {}
        for uti in utis:
            uti_cache[(uti.unit_id, uti.test_id)] = {
                'reference': uti.reference_id,
                'tolerance': uti.tolerance_id,
                'test': uti.test_id,
            }

        for site in sites:

            if site:  # site can be None here since not all units may have a site
                site = umodels.Site.objects.get(pk=site)

            sites_data.append((site.name if site else "", []))
            for utc in self.get_utcs_for_site(self.filter_set.qs, site):

                all_lists = utc.tests_object.test_list_members().prefetch_related("testlistmembership_set__test",)
                for li in all_lists:

                    li.utis = []
                    for test in li.ordered_tests():
                        uti = uti_cache[utc.unit_id, test.id]
                        ref = ref_cache[uti['reference']] if uti['reference'] else None
                        tol = tol_cache[uti['tolerance']] if uti['tolerance'] else None
                        cat = cat_cache[test.id]
                        li.utis.append((test, cat, ref, tol))

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
            "frequency__nominal_interval",
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

        for site, utcs in context['sites_data']:
            for utc in utcs:
                rows.extend([
                    (_("Site"), site or _("Other")),
                    (_("Unit"), utc['unit_name']),
                    (_("Test list (Cycle)"), utc['name']),
                    (_("Frequency"), utc['frequency']),
                    (_("Assigned To"), utc['assigned_to']),
                    (_("Link"), utc['link']),
                ])
                is_cycle = len(utc['all_lists']) > 0
                for idx, test_list in enumerate(utc['all_lists']):
                    rows.append((_("Test List"), test_list.name))
                    if is_cycle:
                        rows.append((_("Cycle Day"), idx + 1))

                    rows.append((_("Test"), _("Category"), _("Reference"), _("Tolerance")))
                    rows.extend(test_list.utis)
                    rows.append([])

                rows.append([])

        return rows


class PaperBackupForms(AssignedQCDetailsReport):

    report_type = "qc-paper-backup-forms"
    name = _l("QC Paper Backup Forms")
    filter_class = filters.UnitTestCollectionFilter
    description = mark_safe(_l(
        "This report generates pdf backup forms which can be used in place of QATrack+ "
        "in case your QATrack+ installation is offline for some reason."
    ))
    category = _l("QC Backup Forms")

    template = "reports/qc/backup_forms.html"
    formats = [PDF]
