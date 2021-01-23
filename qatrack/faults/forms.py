from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import gettext_lazy as _l
from form_utils.forms import BetterModelForm

from qatrack.faults import models
from qatrack.service_log import models as sl_models
from qatrack.service_log.forms import ServiceEventMultipleField
from qatrack.units import models as u_models
from qatrack.units.forms import unit_site_unit_type_choices

NEW_FAULT_TYPE_MARKER = "newft:"


class FaultForm(BetterModelForm):

    prefix = "fault"

    comment = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text=_l("Include any relevant comments."),
    )

    unit = forms.ChoiceField(
        label=_l("Unit"),
        help_text=_l("Select the unit this fault occurred on"),
        required=True,
    )

    fault_type_field = forms.CharField(
        label=_l("Fault Type"),
        help_text=_l("Select the fault type that occurred, or enter a new fault type code"),
        widget=forms.Select(),
        required=True,
    )

    related_service_events = ServiceEventMultipleField(
        required=False,
        queryset=sl_models.ServiceEvent.objects.none(),
        label=_l('Related Service Events'),
        help_text=models.Fault._meta.get_field('related_service_events').help_text,
    )

    class Meta:
        model = models.Fault
        fields = [
            'occurred',
            'unit',
            'modality',
            'treatment_technique',
            'fault_type_field',
            'related_service_events',
            'comment',
        ]

    def __init__(self, *args, **kwargs):

        include_related_ses = kwargs.pop("include_related_ses", True)

        super().__init__(*args, **kwargs)

        if not include_related_ses:
            self.fields.pop('related_service_events')

        instance = kwargs.get('instance')
        if instance and instance.id:
            # if we are editing an existing fault, we need to set up the initial
            # choices otherwise the fault_type_field will be blank
            self.initial['fault_type_field'] = instance.fault_type.code
            self.fields['fault_type_field'].widget.choices = [
                (instance.fault_type.code, instance.fault_type.code),
            ]

            self.fields.pop('comment')

            if include_related_ses:
                # set initial related service events to whatever is set on the model
                self.initial['related_service_events'] = self.instance.related_service_events.all()
                self.fields['related_service_events'].queryset = self.initial['related_service_events']
        elif include_related_ses:
            # on invalid create form submit, we need to reset the related service events to whatever the user posted
            if '%s-related_service_events' % self.prefix in self.data:
                self.fields['related_service_events'].queryset = sl_models.ServiceEvent.objects.filter(
                    pk__in=self.data.getlist('%s-related_service_events' % self.prefix),
                )

            # disable related service event fields if unit not set
            if '%s-unit' % self.prefix not in self.data and 'unit' not in self.initial:
                self.fields['related_service_events'].widget.attrs.update({'disabled': True})
            if '%s-unit' % self.prefix in self.data:
                if not self.data['%s-unit' % self.prefix]:
                    self.fields['related_service_events'].widget.attrs.update({'disabled': True})

        self.fields['unit'].choices = unit_site_unit_type_choices(include_empty=True)

        for f in self.fields:
            self.fields[f].widget.attrs['class'] = 'form-control'

            # since we are dynamically grabbing fault type, we need to set the initial
            # choices to whatever user had it set to
            data_key = '%s-fault_type_field' % self.prefix
            if f == 'fault_type_field' and self.data.get(data_key):
                val = self.data.get(data_key)
                label = val
                if NEW_FAULT_TYPE_MARKER in label:
                    # if the user submitted a new fault type, add asteriks to the label
                    label = "*%s*" % label.replace(NEW_FAULT_TYPE_MARKER, "")
                self.fields[f].widget.choices = [(val, label)]

        if 'comment' in self.fields:
            self.fields['comment'].widget.attrs['class'] += 'autosize'
            self.fields['comment'].widget.attrs['cols'] = 8

    def clean_fault_type_field(self):
        fault_type = self.cleaned_data.get('fault_type_field')
        if fault_type and NEW_FAULT_TYPE_MARKER in fault_type:
            fault_type = fault_type.replace(NEW_FAULT_TYPE_MARKER, "")
            models.FaultType.objects.get_or_create(code=fault_type)

        return fault_type

    def clean_unit(self):
        unit = self.cleaned_data.get('unit')
        if unit:
            try:
                unit = u_models.Unit.objects.get(pk=unit)
            except u_models.Unit.DoesNotExist:  # pragma: nocover
                raise ValidationError('Unit with id %s does not exist' % unit)
        return unit


class ReviewFaultForm(BetterModelForm):

    prefix = "fault"

    class Meta:
        model = models.Fault
        fields = []
