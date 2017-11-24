
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.timezone import timedelta
from django.utils.translation import ugettext as _

from qatrack.parts import models as p_models
from qatrack.service_log import models as sl_models
from qatrack.units import models as u_models
from qatrack.service_log.forms import HoursMinDurationField


def max_24hr(value):
    if value > timedelta(hours=24):

        seconds = value.total_seconds()
        hours = seconds // 3600
        mins = (seconds % 3600) // 60

        raise ValidationError(
            _('Duration can not be greater than 24 hours')
        )


class UnitAvailableTimeForm(forms.ModelForm):

    hours_monday = HoursMinDurationField(help_text='Hours available on mondays (hh:mm)', label='Monday', validators=[max_24hr])
    hours_tuesday = HoursMinDurationField(help_text='Hours available on tuesdays (hh:mm)', label='Tuesday', validators=[max_24hr])
    hours_wednesday = HoursMinDurationField(help_text='Hours available on wednesdays (hh:mm)', label='Wednesday', validators=[max_24hr])
    hours_thursday = HoursMinDurationField(help_text='Hours available on thursdays (hh:mm)', label='Thursday', validators=[max_24hr])
    hours_friday = HoursMinDurationField(help_text='Hours available on fridays (hh:mm)', label='Friday', validators=[max_24hr])
    hours_saturday = HoursMinDurationField(help_text='Hours available on saturdays (hh:mm)', label='Saturday', validators=[max_24hr])
    hours_sunday = HoursMinDurationField(help_text='Hours available on sundays (hh:mm)', label='Sunday', validators=[max_24hr])

    units = forms.ModelMultipleChoiceField(queryset=u_models.Unit.objects.all(), required=False)

    now = timezone.now()
    year_select = forms.ChoiceField(
        required=False, choices=[(y, y) for y in range(now.year - 20, now.year + 10)], initial=now.year
    )
    month_select = forms.ChoiceField(
        required=False, choices=[
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
        initial=now.month - 1
    )

    class Meta:
        model = u_models.UnitAvailableTime
        fields = (
            'date_changed', 'hours_monday', 'hours_tuesday', 'hours_wednesday', 'hours_thursday', 'hours_friday',
            'hours_saturday', 'hours_sunday', 'units'
        )

    def __init__(self, *args, **kwargs):
        super(UnitAvailableTimeForm, self).__init__(*args, **kwargs)

        for f in self.fields:
            if f == 'date_changed':
                self.fields[f].widget.attrs['class'] = 'form-control vDateField'
                self.fields[f].input_formats = ['%d-%m-%Y', '%Y-%m-%d']
            elif f in ['year_select', 'month_select']:
                self.fields[f].widget.attrs['class'] = 'form-control'
            else:
                self.fields[f].widget.attrs['class'] = 'form-control duration weekday-duration'


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
                self.fields[f].input_formats = ['%d-%m-%Y', '%Y-%m-%d']
            elif f == 'hours':
                self.fields[f].widget.attrs['class'] = 'form-control duration'
            elif f == 'units':
                self.fields[f].widget.attrs['id'] = 'id_edit_units'
            else:
                self.fields[f].widget.attrs['class'] = 'form-control'
