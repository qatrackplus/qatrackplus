from itertools import groupby

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.timezone import timedelta
from django.utils.translation import gettext as _

from qatrack.service_log import models as sl_models
from qatrack.service_log.forms import HoursMinDurationField
from qatrack.units import models as u_models


def max_24hr(value: timedelta) -> None:
    """Raise a validation error if input timedelta has a duration greater than 24hrs"""
    if value > timedelta(hours=24):
        raise ValidationError(_('Duration can not be greater than 24 hours'))


year_select = forms.ChoiceField(
    required=False,
    choices=[(y, y) for y in range(timezone.now().year - 20, timezone.now().year + 10)],
    initial=timezone.now().year
).widget.render('year_select', timezone.now().year, attrs={'id': 'id_year_select'})

month_select = forms.ChoiceField(
    required=False,
    choices=[
        (0, 'January'),
        (1, 'February'),
        (2, 'March'),
        (3, 'April'),
        (4, 'May'),
        (5, 'June'),
        (6, 'July'),
        (7, 'August'),
        (8, 'September'),
        (9, 'October'),
        (10, 'November'),
        (11, 'December'),
    ],
    initial=timezone.now().month - 1
).widget.render(
    'month_select', timezone.now().month - 1, attrs={'id': 'id_month_select'}
)


class UnitAvailableTimeForm(forms.ModelForm):

    hours_sunday = HoursMinDurationField(
        help_text='Hours available on sundays (hh:mm)', label='Sunday', validators=[max_24hr]
    )
    hours_monday = HoursMinDurationField(
        help_text='Hours available on mondays (hh:mm)', label='Monday', validators=[max_24hr]
    )
    hours_tuesday = HoursMinDurationField(
        help_text='Hours available on tuesdays (hh:mm)', label='Tuesday', validators=[max_24hr]
    )
    hours_wednesday = HoursMinDurationField(
        help_text='Hours available on wednesdays (hh:mm)', label='Wednesday', validators=[max_24hr]
    )
    hours_thursday = HoursMinDurationField(
        help_text='Hours available on thursdays (hh:mm)', label='Thursday', validators=[max_24hr]
    )
    hours_friday = HoursMinDurationField(
        help_text='Hours available on fridays (hh:mm)', label='Friday', validators=[max_24hr]
    )
    hours_saturday = HoursMinDurationField(
        help_text='Hours available on saturdays (hh:mm)', label='Saturday', validators=[max_24hr]
    )

    unit = forms.ModelChoiceField(widget=forms.HiddenInput(), queryset=u_models.Unit.objects.all())

    class Meta:
        model = u_models.UnitAvailableTime
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(UnitAvailableTimeForm, self).__init__(*args, **kwargs)

        for f in self.fields:
            if f == 'date_changed':
                self.fields[f].widget.attrs['class'] = 'form-control vDateField'
                self.fields[f].input_formats = settings.DATE_INPUT_FORMATS
            else:
                self.fields[f].widget.attrs['class'] = 'form-control duration weekday-duration'

        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            self.fields['hours_' + day].widget.attrs['placeholder'] = day

            if not self.instance.pk:
                self.fields['hours_' + day].initial = settings.DEFAULT_AVAILABLE_TIMES['hours_' + day]

    def clean_date_changed(self):
        date_changed = self.cleaned_data['date_changed']
        unit = self.cleaned_data.get('unit')
        if not date_changed:
            self.add_error('date_changed', 'Date Changed is a required field')
        elif unit and date_changed < unit.date_acceptance:
            self.add_error('date_changed', 'Date changed cannot be before units acceptance date')
        return date_changed


class UnitAvailableTimeEditForm(forms.ModelForm):

    units = forms.ModelMultipleChoiceField(queryset=u_models.Unit.objects.all())
    hours = HoursMinDurationField(help_text='Hours available (hh:mm)', label='Hours', validators=[max_24hr])

    class Meta:
        model = u_models.UnitAvailableTimeEdit
        fields = ('date', 'hours', 'name', 'units')

    def __init__(self, *args, **kwargs):
        super(UnitAvailableTimeEditForm, self).__init__(*args, **kwargs)

        for f in self.fields:
            if f == 'date':
                self.fields[f].widget.attrs['class'] = 'form-control vDateField'
                self.fields[f].input_formats = settings.DATE_INPUT_FORMATS
            elif f == 'hours':
                self.fields[f].widget.attrs['class'] = 'form-control duration'
            elif f == 'units':
                self.fields[f].widget.attrs['id'] = 'id_edit_units'
            else:
                self.fields[f].widget.attrs['class'] = 'form-control'

    def clean_date(self):
        cleaned = self.cleaned_data['date']
        if cleaned < self.instance.unit.date_acceptance:
            raise ValidationError('Unit cannot have available time edit before it\'s date of acceptance.')
        return cleaned


def unit_site_unit_type_choices(include_empty=False, serviceable_only=False):
    """Return units grouped by site and unit type, suitable for using as optgroups for select inputs"""

    def site_unit_type(u):
        return "%s :: %s" % (u.site.name, u.type.name)

    def site_unit_name(u):
        return "%s :: %s" % (u.site.name, u.name)

    units = u_models.Unit.objects.select_related(
        "site",
        "type",
    ).order_by("site__name", "type__name", settings.ORDER_UNITS_BY)

    if serviceable_only:
        units = units.filter(is_serviceable=True)

    choices = [(ut, list(us)) for (ut, us) in groupby(units, key=site_unit_type)]
    choices = [(ut, [(u.id, site_unit_name(u)) for u in us]) for (ut, us) in choices]
    if include_empty:
        choices = [("", "---------")] + choices

    return choices


def unit_site_service_area_choices(include_empty=False):
    """Return unit service areas grouped by site and unit, suitable for using as optgroups for select inputs"""

    def service_area(usa):
        return usa.service_area.name

    def site_unit_name(usa):
        return "%s :: %s" % (usa.unit.site.name, usa.unit.name)

    usas = sl_models.UnitServiceArea.objects.select_related(
        "unit__site",
        "unit",
        "service_area",
    )

    usas = usas.order_by(
        "unit__site__name",
        "unit__%s" % settings.ORDER_UNITS_BY,
        "service_area__name",
    )

    choices = [(site, list(units)) for (site, units) in groupby(usas, key=site_unit_name)]
    choices = [(site, [(usa.id, service_area(usa)) for usa in units]) for (site, units) in choices]
    if include_empty:
        choices = [("", "---------")] + choices

    return choices


def utc_choices(include_empty=False):
    """Return units grouped by site and unit type, suitable for using as optgroups for select inputs"""

    def site_unit_type(u):
        return "%s :: %s" % (u.site.name, u.type.name)

    units = u_models.Unit.objects.select_related("site", "type").prefetch_related(
        "unittestcollection_set",
    ).order_by("site__name", "type__name", settings.ORDER_UNITS_BY)

    choices = []
    for ut, units in groupby(units, key=site_unit_type):
        choices.append((ut, []))
        for unit in units:
            for utc in sorted(unit.unittestcollection_set.all(), key=lambda uu: uu.name):
                choices[-1][-1].append((utc.pk, "%s :: %s" % (unit.name, utc.name)))

    if include_empty:
        choices = [("", "---------")] + choices

    return choices
