from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa import models
from qatrack.reports import filters
from qatrack.reports.reports import (
    ORDERED_CONTENT_TYPES,
    BaseReport,
    format_user,
)


class TestInstanceDetailsReport(BaseReport):

    report_type = "testinstance_details"
    name = _l("Test Instance Details")
    filter_class = filters.TestDataFilter
    description = mark_safe(_l("This report shows QC test values for select units"))

    category = _l("QC")

    MAX_TIS = getattr(settings, "REPORT_TESTDATAREPORT_MAX_TIS", 365 * 3)

    template = "reports/qc/testinstance_details.html"
    formats = ORDERED_CONTENT_TYPES

    __test__ = False  # supress pytest warning

    def filter_form_valid(self, filter_form):

        ntis = self.filter_set.qs.count()
        if ntis > self.MAX_TIS:
            msg = _(
                "This report can only be generated with %(max_num_test_instances)d or fewer Test "
                "Instances.  Your filters are including %(num_test_instances)d. Please reduce the "
                "number of Tests, Sites, Units, or Work Completed time period."
            ) % {
                'max_num_test_instances': self.MAX_TIS,
                'num_test_instances': ntis
            }
            filter_form.add_error("__all__", msg)

        return filter_form.is_valid()

    def get_queryset(self):
        return models.TestInstance.objects.order_by("work_completed")

    def get_filename(self, report_format):
        return "%s.%s" % (slugify(self.name or _("test-instance-details")), report_format)

    def get_unit_test_info__test_details(self, val):
        return (
            _("Test"),
            ', '.join(models.Test.objects.filter(pk__in=val).order_by("name").values_list("name", flat=True)),
        )

    def get_organization_details(self, val):
        field = self.filter_class().form.fields['organization']
        return (field.label, str(dict(field.choices).get(val, "")))

    def get_context(self):

        context = super().get_context()
        context['qs'] = self.filter_set.qs
        org = self.filter_set.form.cleaned_data['organization']
        if org == "group_by_unit_test_date":
            org = self.get_organization_details(org)[1]
            context['test_data'] = [[
                _(
                    "Sorry, '{organization}' is not supported for Preview or PDF reports. "
                    "Switch to Excel or CSV format, or use 'One Test Instance Per Row'"
                ).format(organization=org)
            ]]
        else:
            context['test_data'] = self.data_rows()

        return context

    def to_table(self, context):

        rows = super().to_table(context)

        rows.append([])

        test_data = self.data_rows()
        rows.extend(test_data)
        return rows

    def data_rows(self):
        org = self.filter_set.form.cleaned_data['organization']
        if org == "one_per_row":
            test_data = self.organize_one_per_row()
        elif org == "group_by_unit_test_date":
            test_data = self.organize_by_unit_test_date()

        return test_data

    def organize_one_per_row(self):

        qs = self.filter_set.qs.select_related(
            "test_list_instance",
            "unit_test_info__test",
            "unit_test_info__unit",
            "unit_test_info__unit__site",
            "reference",
            "tolerance",
            "created_by",
        )

        headers = [[
            _("Work Completed"),
            _("Test"),
            _("Unit"),
            _("Site"),
            _("Value"),
            _("Reference"),
            _("Tolerance"),
            _("Skipped"),
            _("Performed By"),
            _("Comment"),
        ]]

        table = headers
        for ti in qs:

            uti = ti.unit_test_info

            table.append([
                ti.test_list_instance.work_completed,
                uti.test.name,
                uti.unit.name,
                uti.unit.site.name if uti.unit.site else "",
                ti.value_display(),
                ti.reference.value_display() if ti.reference else "",
                ti.tolerance.name if ti.tolerance else "",
                ti.skipped,
                format_user(ti.created_by),
                ti.comment,
            ])

        return table

    def organize_by_unit_test_date(self):

        qs = self.filter_set.qs
        unit_test_combos = list(qs.values_list(
            "unit_test_info__unit",
            "unit_test_info__test",
        ).order_by(
            "unit_test_info__unit__%s" % settings.ORDER_UNITS_BY,
            "unit_test_info__test__display_name",
        ).distinct())

        unique_dates = list(qs.order_by(
            "test_list_instance__work_completed",
        ).values_list(
            "test_list_instance__work_completed",
            flat=True,
        ))

        cells_per_ti = 5
        date_rows = {d: i for i, d in enumerate(unique_dates)}
        ut_cols = {ut: i * cells_per_ti for i, ut in enumerate(unit_test_combos)}

        tests = dict(qs.values_list("unit_test_info__test_id", "unit_test_info__test__name").distinct())

        unit_qs = qs.values_list(
            "unit_test_info__unit_id",
            "unit_test_info__unit__site__name",
            "unit_test_info__unit__name",
        ).distinct()
        units = {}
        for unit_id, site_name, unit_name in unit_qs:
            units[unit_id] = "%s : %s" % (site_name or _("Other"), unit_name)

        table = [[_("Date")]]

        for unit_id, test_id in unit_test_combos:
            table[-1].append("%s - %s" % (units[unit_id], tests[test_id]))
            table[-1].append(_("Reference"))
            table[-1].append(_("Tolerance"))
            table[-1].append(_("Peformed By"))
            table[-1].append(_("Comment"))

        ncombos = len(unit_test_combos)
        table += [[ut] + [""] * (cells_per_ti * ncombos) for ut in unique_dates]

        wc_cache = dict(qs.values_list("pk", "test_list_instance__work_completed"))
        for unit_id, test_id in unit_test_combos:

            tis = qs.filter(
                unit_test_info__unit_id=unit_id, unit_test_info__test_id=test_id,
            ).select_related(
                "unit_test_info__test",
                "reference",
                "tolerance",
                "created_by",
            )
            for ti in tis:
                val = ti.value_display(coerce_numerical=False)
                ref = ti.reference.value_display() if ti.reference else ''
                tol = ti.tolerance.name if ti.tolerance else ''
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 1] = val
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 2] = ref
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 3] = tol
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 4] = format_user(ti.created_by)
                table[date_rows[wc_cache[ti.pk]] + 1][ut_cols[(unit_id, test_id)] + 5] = ti.comment

        return table
