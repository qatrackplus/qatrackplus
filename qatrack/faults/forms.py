from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import gettext_lazy as _l
from django.utils.text import slugify
from form_utils.forms import BetterModelForm

from qatrack.faults import models
from qatrack.units import models as u_models
from qatrack.units.forms import unit_site_unit_type_choices

NEW_FAULT_TYPE_MARKER = "newft:"


class FaultForm(BetterModelForm):

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
        fieldsets = [
            ('hidden_fields', {
                'fields': [],
            }),
            ('required_fields', {
                'fields': [
                    'occurred',
                    'unit',
                    'modality',
                    'fault_type_field',
                ],
            }),
            ('optional_fields', {
                'fields': [
                    'comment',
                ]
            })
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['unit'].choices = unit_site_unit_type_choices(include_empty=True)

        for f in self.fields:
            self.fields[f].widget.attrs['class'] = 'form-control'
            if f == 'fault_type_field' and self.data.get('fault_type_field'):
                val = self.data.get('fault_type_field')
                label = val
                if NEW_FAULT_TYPE_MARKER in label:
                    label = "*%s*" % label.replace(NEW_FAULT_TYPE_MARKER, "")
                self.fields[f].widget.choices = [(val, label)]

        for f in ['comment']:
            self.fields[f].widget.attrs['class'] += 'autosize'
            self.fields[f].widget.attrs['cols'] = 8

    def clean_fault_type_field(self):
        fault_type = self.cleaned_data.get('fault_type_field')
        if fault_type:
            fault_type = fault_type.replace(NEW_FAULT_TYPE_MARKER, "")
            fault_type, __ = models.FaultType.objects.get_or_create(
                code=fault_type,
                defaults={
                    'description': '',
                    'slug': slugify(fault_type),
                }
            )
        return fault_type

    def clean_unit(self):
        unit = self.cleaned_data.get('unit')
        if unit:
            try:
                unit = u_models.Unit.objects.get(pk=unit)
            except u_models.Unit.DoesNotExist:
                raise ValidationError('Unit with id %s does not exist' % unit)
        return unit
