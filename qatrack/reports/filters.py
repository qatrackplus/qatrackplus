from itertools import groupby

import dateutil.parser
from django import forms
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
import django_filters

from qatrack.qa import models
from qatrack.qatrack_core.utils import relative_dates
from qatrack.service_log import models as sl_models
from qatrack.units import models as umodels
from qatrack.units.forms import unit_site_unit_type_choices, utc_choices


class NonNullBooleanFilter(django_filters.filters.BooleanFilter):
    field_class = forms.BooleanField


class RelativeDateRangeField(forms.fields.CharField):

    def clean(self, value):

        val = super().clean(value)

        custom = val.lower() not in relative_dates.ALL_DATE_RANGES
        if not custom:
            return val

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


class RelativeDateRangeFilter(django_filters.CharFilter):
    """Date range filter to use in conjunction with bootstrap daterangepicker"""

    field_class = RelativeDateRangeField

    def filter(self, qs, value):

        if not value:
            return qs  # pragma: no cover

        try:
            start_date, end_date = relative_dates(value).range()
        except:  # noqa: E722
            # custom period
            start_date, end_date = value

        fn = self.field_name
        qs = qs.filter(**{"%s__gte" % fn: start_date}).filter(**{"%s__lte" % fn: end_date})
        return qs.distinct() if self.distinct else qs


class BaseReportFilterSet(django_filters.FilterSet):

    def filter_queryset(self, queryset):
        """
        Remove non model field filters before filtering then add them back so
        they get passed to report/saved to DB.
        """
        non_model_fields = {}
        for field in list(self.form.cleaned_data.keys()):
            if field not in self.Meta.fields:
                non_model_fields[field] = self.form.cleaned_data.pop(field)

        qs = super().filter_queryset(queryset)
        self.form.cleaned_data.update(non_model_fields)
        return qs


class TestListInstanceFilter(BaseReportFilterSet):

    work_completed = RelativeDateRangeFilter(
        label=_l("Work Completed"),
        help_text=_l("Dates to include QC data from"),
    )

    unit_test_collection__unit__site = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Site"),
        null_label=_l("Other"),
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
        queryset=models.Group.objects.order_by("name"),
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


class TestListInstanceByUTCFilter(BaseReportFilterSet):

    work_completed = RelativeDateRangeFilter(
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


class UnitTestCollectionFilter(BaseReportFilterSet):

    assigned_to = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Assigned To"),
        queryset=models.Group.objects.order_by("name"),
        help_text=_l(
            "Use this filter to limit report to one or more groups (leave blank to include all units)"
        ),
    )

    unit__site = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Site"),
        null_label=_l("Other"),
        queryset=umodels.Site.objects.all(),
        help_text=_l("Use this filter to limit report to one or more sites (leave blank to include all units)"),
    )

    unit = django_filters.filters.MultipleChoiceFilter(
        label=_l("Unit"),
        help_text=_l("Use this filter to limit report to one or more units (leave blank to include all units)"),
    )

    frequency = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Frequency"),
        queryset=models.Frequency.objects.all(),
        null_label=_l("Ad Hoc"),
        help_text=_l("Use this filter to limit report to one or more frequencies (leave blank to include all units)"),
    )

    active = django_filters.filters.BooleanFilter(
        label=_l("Active"),
        help_text=_l("Select whether you want to include assignments which are Active, Inactive, or Both"),
        initial='2',
    )

    class Meta:
        model = models.UnitTestCollection
        fields = ["unit__site", "unit", "frequency", "assigned_to", "active"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.form.fields['unit'].choices = unit_site_unit_type_choices()
        self.form.fields['active'].widget.choices = (
            ('1', _('Both')),
            ('2', _('Yes')),
            ('3', _('No')),
        )


class UnitTestCollectionFilterDetailsMixin:

    def get_unit__site_details(self, val):
        sites = [x.name if x != "null" else "Other" for x in val]
        return ("Site(s)", ", ".join(sites))

    def get_unit_details(self, val):
        units = models.Unit.objects.select_related("site").filter(pk__in=val)
        units = ('%s - %s' % (u.site.name if u.site else _("Other"), u.name) for u in units)
        return ("Unit(s)", ', '.join(units))

    def get_frequency_details(self, val):
        freqs = [x.name if x != "null" else "Ad Hoc" for x in val]
        return ("Frequencies", ", ".join(freqs))

    def get_active_details(self, val):
        if val is None:
            det = _("Either")
        else:
            det = [_("No"), _("Yes")][val]
        return (_("Active Only"), det)


class SchedulingFilter(BaseReportFilterSet):

    due_date = RelativeDateRangeFilter(
        label=_l("Time Period"),
        help_text=_l("Dates to include scheduled QC data from"),
    )

    assigned_to = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Assigned To"),
        queryset=models.Group.objects.order_by("name"),
        help_text=_l(
            "Use this filter to limit report to one or more groups (leave blank to include all units)"
        ),
    )

    unit__site = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Site"),
        null_label=_l("Other"),
        queryset=umodels.Site.objects.all(),
        help_text=_l("Use this filter to limit report to one or more sites (leave blank to include all units)"),
    )

    unit = django_filters.filters.MultipleChoiceFilter(
        label=_l("Unit"),
        help_text=_l("Use this filter to limit report to one or more units (leave blank to include all units)"),
    )

    frequency = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Frequency"),
        queryset=models.Frequency.objects.all(),
        null_label=_l("Ad Hoc"),
        help_text=_l("Use this filter to limit report to one or more frequencies (leave blank to include all units)"),
    )

    active = django_filters.filters.BooleanFilter(
        label=_l("Active"),
        help_text=_l("Select whether you want to include assignments which are Active, Inactive, or Both"),
        initial='2',
    )

    class Meta:
        model = models.UnitTestCollection
        fields = ["due_date", "assigned_to", "unit__site", "unit"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.form.fields['due_date'].widget.attrs['class'] = "futuredate"
        self.form.fields['unit'].choices = unit_site_unit_type_choices()
        self.form.fields['active'].widget.choices = (
            ('1', _('Both')),
            ('2', _('Yes')),
            ('3', _('No')),
        )


class TestDataFilter(BaseReportFilterSet):

    test_list_instance__work_completed = RelativeDateRangeFilter(
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
        null_label=_l("Other"),
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

        self.form.fields['test_list_instance__work_completed'].widget.attrs['class'] = "pastdate"
        self.form.fields['test_list_instance__work_completed'].initial = "Last 365 days"
        self.form.fields['unit_test_info__unit'].choices = unit_site_unit_type_choices()
        self.form.fields['unit_test_info__test'].choices = test_category_choices()


def test_category_choices():
    tests = []
    qs = models.Test.objects.values("category__name", "pk", "name").order_by("category__name", "name")
    for g, ts in groupby(qs, lambda v: v['category__name']):
        tests.append((g, [(t['pk'], t['name']) for t in ts]))
    return tests


class BaseServiceEventFilter(BaseReportFilterSet):

    datetime_service = RelativeDateRangeFilter(
        label=_l("Service Date"),
        help_text=_l("Dates to include Service Events from"),
    )

    unit_service_area__unit__site = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Site"),
        null_label=_l("Other"),
        queryset=umodels.Site.objects.all(),
        help_text=_l("Use this filter to limit report to one or more sites (leave blank to include all)"),
    )

    unit_service_area__unit = django_filters.filters.MultipleChoiceFilter(
        label=_l("Unit"),
        help_text=_l("Use this filter to limit report to one or more units (leave blank to include all)"),
    )

    unit_service_area__service_area = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Service Area"),
        queryset=sl_models.ServiceArea.objects.order_by("name").all(),
        help_text=_l("Use this filter to limit report to one or more service areas (leave blank to include all)"),
    )

    service_type = django_filters.filters.ModelMultipleChoiceFilter(
        label=_l("Service Type"),
        queryset=sl_models.ServiceType.objects.order_by("name").all(),
        help_text=_l("Use this filter to limit report to one or more service types (leave blank to include all)"),
    )

    class Meta:
        model = sl_models.ServiceEvent
        fields = ["datetime_service", "unit_service_area__unit__site", "unit_service_area__unit", "service_type"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.form.fields['unit_service_area__unit'].choices = unit_site_unit_type_choices(serviceable_only=True)
        self.form.fields['datetime_service'].widget.attrs['class'] = "pastdate"
        self.form.fields['datetime_service'].initial = "Last 365 days"


class ServiceEventSummaryFilter(BaseServiceEventFilter):

    include_description = NonNullBooleanFilter(
        label=_l("Include Description"),
        help_text=_l("Uncheck if you don't want to include Problem & Work descriptions in this report"),
        initial=True,
    )


class ServiceEventDetailsFilter(BaseServiceEventFilter):
    pass
