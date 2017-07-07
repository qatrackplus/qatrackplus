
from django import forms
from django.core.exceptions import ValidationError
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

    units = forms.ModelMultipleChoiceField(queryset=u_models.Unit.objects.all())

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
