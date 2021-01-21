from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import gettext_lazy as _l
from form_utils.forms import BetterModelForm

from qatrack.faults import models
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

    class Meta:
        model = models.Fault
        fields = [
            'occurred',
            'unit',
            'modality',
            'treatment_technique',
            'fault_type_field',
            'comment',
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        instance = kwargs.get('instance')
        if instance and instance.id:
            # if we are editing an existing fault, we need to set up the initial
            # choices otherwise the fault_type_field will be blank
            self.initial['fault_type_field'] = instance.fault_type.code
            self.fields['fault_type_field'].widget.choices = [
                (instance.fault_type.code, instance.fault_type.code),
            ]

            self.fields.pop('comment')

        self.fields['unit'].choices = unit_site_unit_type_choices(include_empty=True)

        for f in self.fields:
            self.fields[f].widget.attrs['class'] = 'form-control'
            data_key = '%s-fault_type_field' % self.prefix
            if f == 'fault_type_field' and self.data.get(data_key):
                val = self.data.get(data_key)
                label = val
                if NEW_FAULT_TYPE_MARKER in label:
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
