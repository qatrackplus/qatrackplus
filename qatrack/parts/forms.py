
from django import forms
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db.models import ObjectDoesNotExist, Q
from django.utils.encoding import force_text
from form_utils.forms import BetterModelForm

from qatrack.parts import models as p_models
from qatrack.service_log import models as sl_models
from qatrack.units import models as u_models


class PartChoiceField(forms.ModelChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            part = p_models.Part.objects.get(pk=value)
        except (ValueError, TypeError, p_models.Part.DoesNotExist) as e:
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
        return part


class FromStorageField(forms.ModelChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            storage = p_models.Storage.objects.get(pk=value)
        except (ValueError, TypeError, p_models.Part.DoesNotExist) as e:
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
        return storage


class PartUsedForm(forms.ModelForm):

    from_storage = FromStorageField(
        required=False,
        queryset=p_models.Storage.objects.none()
    )
    part = PartChoiceField(
        queryset=p_models.Part.objects.none(),
        help_text=p_models.PartUsed._meta.get_field('part').help_text
    )

    class Meta:
        model = p_models.PartUsed
        fields = ('part', 'from_storage', 'quantity')

    def __init__(self, *args, **kwargs):
        super(PartUsedForm, self).__init__(*args, **kwargs)

        is_new = self.instance.id is None

        if is_new:

            if '%s-part' % self.prefix in self.data and self.data.get('%s-part' % self.prefix):
                self.fields['part'].queryset = p_models.Part.objects.filter(pk=self.data.get('%s-part' % self.prefix))
            if '%s-from_storage' % self.prefix in self.data and self.data.get('%s-from_storage' % self.prefix):
                self.fields['from_storage'].queryset = p_models.PartStorageCollection.objects.filter(
                    pk=self.data.get('%s-from_storage' % self.prefix)
                )
                s_dict = dict(p_models.PartStorageCollection.objects.filter(
                    pk=self.data.get('%s-from_storage' % self.prefix)
                ).values_list('storage_id', 'quantity'))
                s_qs = p_models.Storage.objects.filter(id__in=s_dict.keys())
                self.fields['from_storage'].queryset = s_qs
                self.fields['from_storage'].choices = [(None, '----------')] + [(s.id, '%s (%s)' % (s.__str__(), s_dict[s.id])) for s in s_qs]

        else:
            self.initial['part'] = self.instance.part
            self.fields['part'].queryset = p_models.Part.objects.filter(pk=self.instance.part.id)
            if self.instance.from_storage:
                self.initial['from_storage'] = self.instance.from_storage
                s_dict = dict(p_models.PartStorageCollection.objects.filter(
                    part=self.instance.part, storage__isnull=False, quantity__gt=0
                ).values_list('storage_id', 'quantity'))
                if self.instance.from_storage.id not in s_dict:
                    s_dict[self.instance.from_storage.id] = 0
            else:
                s_dict = dict(p_models.PartStorageCollection.objects.filter(
                    part=self.instance.part, storage__isnull=False, quantity__gt=0
                ).values_list('storage_id', 'quantity'))
            print('___________')
            print(self.prefix)
            print(s_dict)
            print(s_dict.keys())
            print('^^^^^^^^^^^')
            s_qs = p_models.Storage.objects.filter(id__in=s_dict.keys())
            self.fields['from_storage'].queryset = s_qs
            # Edit choices to insert quantity of part in storage
            self.fields['from_storage'].choices = [(None, '----------')] + [(s.id, '%s (%s)' % (s.__str__(), s_dict[s.id])) for s in s_qs]

        self.fields['part'].widget.attrs['data-prefix'] = self.prefix

        for f in self.fields:
            self.fields[f].widget.attrs['class'] = 'form-control'

        for f in ['from_storage', 'part']:
            self.fields[f].widget.attrs['class'] += ' select2'

        self.fields['quantity'].widget.attrs['class'] += ' parts-used-quantity max-width-50'
        self.fields['part'].widget.attrs['class'] += ' parts-used-part'
        self.fields['from_storage'].widget.attrs['class'] += ' parts-used-from_storage max-width-75'


PartUsedFormset = forms.inlineformset_factory(sl_models.ServiceEvent, p_models.PartUsed, form=PartUsedForm, extra=2)


class PartForm(BetterModelForm):

    _classes = ['form-control']

    class Meta:
        model = p_models.Part
        fieldsets = [
            ('hidden_fields', {
                'fields': [],
            }),
            ('required_fields', {
                'fields': [
                    'description', 'part_category', 'part_number', 'quantity_min'
                ],
            }),
            ('optional_fields', {
                'fields': [
                    'alt_part_number', 'cost', 'notes'
                ]
            })
        ]

    @property
    def classes(self):
        return ' '.join(self._classes)


class SupplierForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
        model = p_models.Supplier


SupplierFormset = forms.inlineformset_factory(
    p_models.Part, p_models.PartSupplierCollection, form=SupplierForm, extra=2
)


class PartStorageCollectionForm(forms.ModelForm):

    # TODO add fields here
    room = forms.ModelChoiceField(
        required=False, help_text=p_models.Storage._meta.get_field('room').help_text,
        queryset=p_models.Room.objects.all()
    )
    # location = AddOnFlyModelChoiceField()

    class Meta:
        model = p_models.PartStorageCollection

        fields = (
            'room',
            # 'location',
            'quantity'
        )


PartStorageCollectionFormset = forms.inlineformset_factory(
    p_models.Part, p_models.PartStorageCollection, form=PartStorageCollectionForm, extra=2
)