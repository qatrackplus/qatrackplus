from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import ObjectDoesNotExist
from django.utils.encoding import force_str
from django.utils.translation import gettext as _
from form_utils.forms import BetterModelForm

from qatrack.parts import models as p_models
from qatrack.service_log import models as sl_models


class PartChoiceField(forms.ModelChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            part = p_models.Part.objects.get(pk=value)
        except (ValueError, TypeError, p_models.Part.DoesNotExist):
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
        return part


class FromStorageField(forms.ModelChoiceField):

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            storage = p_models.Storage.objects.get(pk=value)
        except (ValueError, TypeError, p_models.Part.DoesNotExist):
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
        self.user = kwargs.pop('user')
        super(PartUsedForm, self).__init__(*args, **kwargs)

        is_new = self.instance.id is None

        if is_new:

            if '%s-part' % self.prefix in self.data and self.data.get('%s-part' % self.prefix):
                self.fields['part'].queryset = p_models.Part.objects.filter(pk=self.data.get('%s-part' % self.prefix))
                if '%s-from_storage' % self.prefix in self.data and self.data.get('%s-from_storage' % self.prefix):
                    self.fields['from_storage'].queryset = p_models.PartStorageCollection.objects.filter(
                        part=self.data.get('%s-part' % self.prefix)
                    )
                    s_dict = dict(p_models.PartStorageCollection.objects.filter(
                        part=self.data.get('%s-part' % self.prefix)
                    ).values_list('storage_id', 'quantity'))
                    s_qs = p_models.Storage.objects.filter(id__in=s_dict.keys())
                    self.fields['from_storage'].queryset = s_qs
                    self.fields['from_storage'].choices = [(None, '----------')] + [
                        (s.id, '%s (%s)' % (s.__str__(), s_dict[s.id])) for s in s_qs
                    ]

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

            s_qs = p_models.Storage.objects.filter(id__in=s_dict.keys())
            self.fields['from_storage'].queryset = s_qs
            # Edit choices to insert quantity of part in storage
            self.fields['from_storage'].choices = [(None, '----------')
                                                   ] + [(s.id, '%s (%s)' % (s.__str__(), s_dict[s.id])) for s in s_qs]

        self.fields['part'].widget.attrs['data-prefix'] = self.prefix

        for f in self.fields:
            self.fields[f].widget.attrs['class'] = 'form-control'

        self.fields['quantity'].widget.attrs['class'] += ' parts-used-quantity max-width-50'
        self.fields['part'].widget.attrs['class'] += ' parts-used-part'
        self.fields['from_storage'].widget.attrs['class'] += ' parts-used-from_storage'

    def clean_quantity(self):

        quantity = self.cleaned_data['quantity']
        from_storage = self.cleaned_data.get('from_storage')
        initial_quantity = self.initial.get('quantity', 0)

        if from_storage is not None and ('quantity' in self.changed_data or 'from_storage' in self.changed_data):

            quantity_changed = quantity - initial_quantity
            quantity_storage = p_models.PartStorageCollection.objects.get(
                part=self.cleaned_data['part'], storage=from_storage
            ).quantity

            if from_storage and quantity_changed > quantity_storage:
                self.add_error('quantity', 'Quantity used greater than quantity in storage. {}'.format(
                    '' if initial_quantity == 0 else '(Originally used {})'.format(initial_quantity)
                ))
                self.add_error('from_storage', '')

        if quantity < 1:
            self.add_error('quantity', 'Quantity must be greater than 0')

        return quantity


PartUsedFormset = forms.inlineformset_factory(sl_models.ServiceEvent, p_models.PartUsed, form=PartUsedForm, extra=2)


class CostInputField(forms.CharField):

    widget = forms.TextInput()

    def to_python(self, value):
        value = value.replace('$', '').replace(',', '')
        if value and float(value) < 0:
            raise ValidationError('Ensure this value is greater than or equal to 0.')
        if not value:
            value = None
        return value


class PartForm(BetterModelForm):

    cost = CostInputField(
        help_text=p_models.Part._meta.get_field('cost').help_text,
        required=False,
    )

    part_attachments = forms.FileField(
        label="Attachments",
        max_length=150,
        required=False,
        widget=forms.FileInput(attrs={
            'multiple': '',
            'class': 'file-upload',
            'style': 'display:none',
        })
    )
    part_attachments_delete_ids = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = p_models.Part
        if not settings.PARTS_ALLOW_BLANK_PART_NUM:
            required_fields = ['part_number', 'new_or_used', 'quantity_min']
            optional_fields = ['alt_part_number', 'part_category', 'cost', 'is_obsolete']
        else:
            required_fields = ['new_or_used', 'quantity_min']
            optional_fields = ['part_number', 'alt_part_number', 'part_category', 'cost', 'is_obsolete']

        fieldsets = [
            ('hidden_fields', {
                'fields': [],
            }),
            ('name', {
                'fields': [
                    'name',
                ],
            }),
            ('required_fields', {
                'fields': required_fields,
            }),
            ('optional_fields', {
                'fields': optional_fields,
            }),
            ('notes', {
                'fields': [
                    'notes'
                ]
            })
        ]

    def __init__(self, *args, **kwargs):
        super(PartForm, self).__init__(*args, **kwargs)

        self.fields['quantity_min'].widget.attrs.update({'min': 0, 'step': 1})
        self.fields['quantity_min'].label = 'Low inventory count'

        for f in ['part_number', 'new_or_used', 'cost', 'quantity_min', 'alt_part_number', 'part_category']:
            self.fields[f].widget.attrs['class'] = 'form-control'

        for f in ['name', 'notes']:
            self.fields[f].widget.attrs['class'] = 'form-control autosize'
            self.fields[f].widget.attrs['rows'] = 3
            self.fields[f].widget.attrs['cols'] = 4

        for f in self.Meta.required_fields:
            self.fields[f].widget.attrs['placeholder'] = 'required'

    def clean_part_number(self):
        pn = self.cleaned_data.get("part_number")
        if not pn and not settings.PARTS_ALLOW_BLANK_PART_NUM:
            self.add_error('part_number', 'This field is required')
        return pn


class PartSupplierCollectionForm(forms.ModelForm):

    class Meta:
        fields = ('part', 'supplier', 'part_number')
        model = p_models.PartSupplierCollection

    def __init__(self, *args, **kwargs):
        super(PartSupplierCollectionForm, self).__init__(*args, **kwargs)
        self.fields['part'].widget = forms.HiddenInput()

        self.fields['part_number'].widget.attrs['class'] = 'form-control part_number'
        self.fields['supplier'].widget.attrs['class'] = 'form-control supplier'


PartSupplierCollectionFormset = forms.inlineformset_factory(
    p_models.Part, p_models.PartSupplierCollection, form=PartSupplierCollectionForm, extra=3
)


class LocationField(forms.ChoiceField):

    # Validation really done by hidden storage field
    def validate(self, value):
        return value

    def has_changed(self, initial, data, tliib=False):
        return False


class StorageField(forms.ChoiceField):

    def clean(self, value):
        """

        Args:
            value: Either the pk of the storage as selected by room and location, or a string in the format
            of '__new__<name>'.

        Returns:
            String: if new storage is to be created. Returned value is location of new storage.
            Storage: if value was given as existing storage id.
            (field_name, ValidationError):  To raise ValidationError on related field in form.
        """
        if value in [None, '']:
            return 'room', ValidationError('This field is required')
        elif '__new__' in value:
            value = value.replace('__new__', '')
            if value.strip() == '':
                return 'location', ValidationError('Invalid location')
            return value
        else:
            try:
                storage = p_models.Storage.objects.get(pk=value)
                return storage
            except ObjectDoesNotExist:
                return 'room', ValidationError("Incorrect Storage value")

    def has_changed(self, initial, data, tliib=False):
        if initial is None:
            if data in [None, '']:
                return False
            return True
        else:
            return force_str(initial) != force_str(data)


class PartStorageCollectionForm(forms.ModelForm):

    room = forms.ModelChoiceField(
        required=False, help_text=p_models.Storage._meta.get_field('room').help_text,
        queryset=p_models.Room.objects.all()
    )
    location = LocationField(required=False)
    storage_field = StorageField(widget=forms.TextInput())

    class Meta:
        model = p_models.PartStorageCollection

        fields = ('storage_field', 'room', 'location', 'quantity')

    def __init__(self, *args, **kwargs):
        super(PartStorageCollectionForm, self).__init__(*args, **kwargs)

        is_new = self.instance.id is None

        if not is_new:
            self.initial['room'] = self.instance.storage.room
            self.initial['storage_field'] = self.instance.storage.id
            self.initial['location'] = self.instance.storage.id
            self.fields['location'].widget.choices = [(self.instance.storage.id, '')]

        self.fields['room'].widget.attrs['class'] = 'form-control room'
        self.fields['quantity'].widget.attrs['class'] = 'form-control quantity'
        self.fields['location'].widget.attrs['class'] = 'form-control location'
        self.fields['storage_field'].widget.attrs['class'] = 'storage_field'
        self.fields['location'].widget.attrs.update({'disabled': True})

        location_data = self.data.get('%s-location' % self.prefix, [])
        if '__new__' in location_data:
            self.fields['location'].widget.choices.append(
                (location_data, location_data.replace('__new__', ''))
            )
            self.initial['location'] = location_data

    def clean(self):
        cleaned_data = super(PartStorageCollectionForm, self).clean()
        storage_field_value = cleaned_data.get('storage_field')
        room = cleaned_data.get('room')

        if isinstance(storage_field_value, str):
            if p_models.Storage.objects.filter(location=storage_field_value, room=room).exists():
                self.add_error(None, 'New room/location combination already exists.')
        elif isinstance(storage_field_value, p_models.Storage):
            if room is None or storage_field_value.room_id != room.id:
                self.add_error(None, 'Incorrect room/storage combination.')
        elif isinstance(storage_field_value, tuple):
            self.add_error(storage_field_value[0], storage_field_value[1])

        return cleaned_data

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity < 0:
            self.add_error('quantity', 'Quantity must be greater than 0')
        return quantity


BasePartStorageCollectionFormset = forms.inlineformset_factory(
    p_models.Part, p_models.PartStorageCollection, form=PartStorageCollectionForm, extra=3
)


class PartStorageCollectionFormset(BasePartStorageCollectionFormset):

    def clean(self):
        if any(self.errors):
            return

        locations = []

        for form in self.forms:
            room = form.cleaned_data.get('room')
            loc = form.cleaned_data.get('location')
            if room is None or (self.can_delete and self._should_delete_form(form)):
                continue

            if (room, loc) in locations:
                raise ValidationError(_("Duplicated storage locations are not allowed"))
            locations.append((room, loc))
