from itertools import groupby

import dateutil.parser
from django import forms
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _l
import django_filters

from qatrack.qa import models
from qatrack.qatrack_core.utils import format_datetime_as_date
from qatrack.units import models as umodels
from qatrack.units.forms import unit_site_unit_type_choices, utc_choices


class CustomDateRangeField(forms.fields.CharField):

    def clean(self, value):
        val = super().clean(value)
        try:
            is_dashed_format = val.count("-") == 5
            if is_dashed_format:
                explode = val.split("-")
                start = '-'.join(explode[:3])
                end = '-'.join(explode[3:])
            else:
                start, end = [x.strip() for x in val.split("-")]
            tz = timezone.get_current_timezone()
            start = tz.localize(dateutil.parser.parse(start))
            end = tz.localize(dateutil.parser.parse(end)).replace(hour=23, minute=59, second=59)
        except:  # noqa: E722
            raise forms.ValidationError("Format must be a range e.g. 01 Jan 2000 - 01 Feb 2000", code="invalid")

        return start, end


class CustomDateRangeFilter(django_filters.CharFilter):
    """Date range filter to use in conjunction with bootstrap daterangepicker"""

    field_class = CustomDateRangeField

    def filter(self, qs, value):

        if not value:
            return qs  # pragma: no cover

        fn = self.field_name
        qs = qs.filter(**{"%s__gte" % fn: value[0]}).filter(**{"%s__lte" % fn: value[1]})
        return qs.distinct() if self.distinct else qs


class TestListInstanceFilter(django_filters.FilterSet):

    work_completed = CustomDateRangeFilter(
        label=_l("Work Completed"),
        help_text=_l("Dates to include QC data from"),
    )

    unit_test_collection__unit__site = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Site"),
        null_label=_l("No Site Assigned"),
        queryset=umodels.Site.objects.all(),
        help_text=_l("Use this filter to limit report to one or more sites (leave blank to include all units)"),
    )

    unit_test_collection__unit = django_filters.filters.MultipleChoiceFilter(
        label=_l("Unit"),
        help_text=_l("Use this filter to limit report to one or more units (leave blank to include all units)"),
    )

    unit_test_collection__frequency = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Frequency"),
        queryset=models.Frequency.objects.all(),
        null_label=_l("Ad Hoc"),
        help_text=_l("Use this filter to limit report to one or more frequencies (leave blank to include all units)"),
    )

    unit_test_collection__assigned_to = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Assigned To"),
        queryset=models.Group.objects.all(),
        help_text=_l(
            "Use this filter to limit report to one or more QC performing groups (leave blank to include all units)"
        ),
    )

    class Meta:
        model = models.TestListInstance
        fields = [
            "work_completed",
            "unit_test_collection__unit__site",
            "unit_test_collection__unit",
            'unit_test_collection__frequency',
            'unit_test_collection__assigned_to',
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.form.fields['work_completed'].widget.attrs['class'] = "pastdate"
        self.form.fields['unit_test_collection__unit'].choices = unit_site_unit_type_choices()


class UnitTestCollectionFilter(django_filters.FilterSet):

    work_completed = CustomDateRangeFilter(
        label=_l("Work Completed"),
        help_text=_l("Dates to include QC data from"),
    )

    unit_test_collection = django_filters.filters.MultipleChoiceFilter(
        label=_l("Test List (Cycle) Assignment"),
        help_text=_l("Select the Unit Test List (Cycle) Assignment)"),
        required=True,
    )

    class Meta:
        model = models.TestListInstance
        fields = [
            "work_completed",
            "unit_test_collection",
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.form.fields['work_completed'].widget.attrs['class'] = "pastdate"
        self.form.fields['unit_test_collection'].choices = utc_choices()


class DueAndOverdueFilter(django_filters.FilterSet):

    assigned_to = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Assigned To"),
        queryset=models.Group.objects.all(),
        help_text=_l(
            "Use this filter to limit report to one or more groups (leave blank to include all units)"
        ),
    )

    unit__site = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Site"),
        null_label=_l("No Site Assigned"),
        queryset=umodels.Site.objects.all(),
        help_text=_l("Use this filter to limit report to one or more sites (leave blank to include all units)"),
    )

    unit = django_filters.filters.MultipleChoiceFilter(
        label=_l("Unit"),
        help_text=_l("Use this filter to limit report to one or more units (leave blank to include all units)"),
    )

    class Meta:
        model = models.UnitTestCollection
        fields = ["assigned_to", "unit", "unit__site"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.form.fields['unit'].choices = unit_site_unit_type_choices()


class SchedulingFilter(django_filters.FilterSet):

    due_date = CustomDateRangeFilter(
        label=_l("Time Period"),
        help_text=_l("Dates to include scheduled QC data from"),
    )

    assigned_to = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Assigned To"),
        queryset=models.Group.objects.all(),
        help_text=_l(
            "Use this filter to limit report to one or more groups (leave blank to include all units)"
        ),
    )

    unit__site = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Site"),
        null_label=_l("No Site Assigned"),
        queryset=umodels.Site.objects.all(),
        help_text=_l("Use this filter to limit report to one or more sites (leave blank to include all units)"),
    )

    unit = django_filters.filters.MultipleChoiceFilter(
        label=_l("Unit"),
        help_text=_l("Use this filter to limit report to one or more units (leave blank to include all units)"),
    )

    class Meta:
        model = models.UnitTestCollection
        fields = ["due_date", "assigned_to", "unit", "unit__site"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.form.fields['due_date'].widget.attrs['class'] = "futuredate"
        self.form.fields['unit'].choices = unit_site_unit_type_choices()


class TestDataFilter(django_filters.FilterSet):

    test_list_instance__work_completed = CustomDateRangeFilter(
        label=_l("Work Completed"),
        help_text=_l("Dates to include QC data from"),
    )

    unit_test_info__test = django_filters.filters.MultipleChoiceFilter(
        label=_l("Test"),
        help_text=_l("Use this filter to choose which tests to include in the report"),
        required=True,
    )

    unit_test_info__unit__site = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Site"),
        null_label=_l("No Site Assigned"),
        queryset=umodels.Site.objects.all(),
        help_text=_l("Use this filter to limit report to one or more sites (leave blank to include all units)"),
    )

    unit_test_info__unit = django_filters.filters.MultipleChoiceFilter(
        label=_l("Unit"),
        help_text=_l("Use this filter to limit report to one or more units (leave blank to include all units)"),
    )

    organization = django_filters.filters.ChoiceFilter(
        label=_l("Organization"),
        choices=[
            ("one_per_row", _l("One Test Instance Per Row")),
            ("group_by_unit_test_date", _l("Group by Unit/Test/Date")),
        ],
        required=True,
        initial="one_per_row",
    )

    class Meta:
        model = models.TestInstance
        fields = [
            "test_list_instance__work_completed",
            "unit_test_info__test",
            "unit_test_info__unit__site",
            "unit_test_info__unit",
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        now = timezone.now()
        last_year = now - timezone.timedelta(days=365)
        wc_range = "%s - %s" % (format_datetime_as_date(last_year), format_datetime_as_date(now))
        self.form.fields['test_list_instance__work_completed'].widget.attrs['class'] = "pastdate"
        self.form.fields['test_list_instance__work_completed'].initial = wc_range
        self.form.fields['unit_test_info__unit'].choices = unit_site_unit_type_choices()
        self.form.fields['unit_test_info__test'].choices = test_category_choices()

    def filter_queryset(self, queryset):
        """
        Remove extra organization field before filtering
        """
        self.organization = self.form.cleaned_data.pop("organization")
        return super().filter_queryset(queryset)


def test_category_choices():
    tests = []
    qs = models.Test.objects.values("category__name", "pk", "name").order_by("category__name", "name")
    for g, ts in groupby(qs, lambda v: v['category__name']):
        tests.append((g, [(t['pk'], t['name']) for t in ts]))
    return tests
