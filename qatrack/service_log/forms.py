
from django.core import exceptions, validators, checks
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.conf import settings
from django.db.models import Field
from django.forms import ModelForm, ModelChoiceField, Textarea
from django.utils.html import conditional_escape, format_html, html_safe
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from form_utils.forms import BetterModelForm

from qatrack.service_log import models


class SelectizeModelChoiceField(ModelChoiceField):

    def to_python(self, value):
        try:
            return super(SelectizeModelChoiceField, self).to_python(value)
        except ValidationError:
            models.ProblemType.objects.create(name=value)
        return super(SelectizeModelChoiceField, self).to_python(value)


class ServiceEventForm(BetterModelForm):

    unit_field = ModelChoiceField(queryset=models.Unit.objects.all(), label='Unit')
    service_area_field = ModelChoiceField(
        queryset=models.ServiceArea.objects.all(), label='Service Area',
        help_text=_('Select service area (must select unit first)')
    )

    class Meta:

        model = models.ServiceEvent

        fieldsets = [
            ('required_fields', {
                'fields': ['datetime_service', 'unit_field', 'service_area_field', 'service_type', 'service_status', 'problem_description'],
                'classes': ['form-control']
            }),
            # ('group2', {
            #     'fields': ['user_modified_by', 'datetime_modified', 'user_created_by', 'datetime_created', 'user_status_changed_by', 'datetime_status_changed'],
            #     'classes': ['disabled']
            # }),
            ('optional_fields', {
                'fields': ['problem_type', 'service_event_related', 'srn', 'work_description', 'safety_precautions'],
                'classes': ['form-control']
            }),
            ('time_fields', {
                'fields': ['duration_service_time', 'duration_lost_time'],
                'classes': ['form-control']
            }),
        ]

    def __init__(self, *args, **kwargs):
        super(ServiceEventForm, self).__init__(*args, **kwargs)

        is_new = self.instance.id is None
        is_bound = self.is_bound

        # If there is no saved instance yet
        if is_new:
            if 'unit_field' not in self.data:
                self.fields['service_area_field'].widget.attrs.update({'disabled': True})

            # some data was attempted to be submitted already
            if not is_bound:
                self.initial['service_status'] = models.ServiceEventStatus.get_default()

        # if we are editing a saved instance
        else:
            self.initial['unit_field'] = self.instance.unit_service_area_collection.unit
            self.initial['service_area_field'] = self.instance.unit_service_area_collection.service_area
            self.fields['service_event_related'].queryset = models.ServiceEvent.objects.exclude(id=self.instance.id)

        for f in ['safety_precautions', 'problem_description', 'work_description']:
            self.fields[f].widget.attrs.update({'rows': 3, 'class': 'autosize'})

        for f in ['unit_field', 'service_area_field', 'service_type', 'service_event_related', 'service_status', 'problem_type']:
            self.fields[f].widget.attrs['class'] = 'select2'

        for f in ['datetime_service']:
            self.fields[f].widget.attrs['class'] = 'daterangepicker-input'
            self.fields[f].input_formats = settings.INPUT_DATE_FORMATS

    def is_valid(self):
        print('-----------------------------')
        print(self.data)
        valid = super(ServiceEventForm, self).is_valid()
        print('``````````````````````````````')
        print(self.cleaned_data)
        print('================================')
        return valid

    def save(self, *args, **kwargs):

        unit = self.cleaned_data.get('unit_field')
        service_area = self.cleaned_data.get('service_area_field')

        usac = models.UnitServiceArea.objects.get(unit=unit, service_area=service_area)

        self.instance.unit_service_area_collection = usac

        super(ServiceEventForm, self).save(*args, **kwargs)

        return self.instance


