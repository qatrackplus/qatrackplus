from django import forms
from django.utils.safestring import mark_safe


class MultipleCharField(forms.CharField):
    widget = forms.SelectMultiple

    def to_python(self, value):
        return value


class UserChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return obj.get_full_name()


class Fieldset:
    def __init__(self, form, name, boundfields, legend='', classes='', description=''):
        self.form = form
        self.name = name
        self.boundfields = boundfields
        self.legend = legend
        self.classes = classes
        self.description = description

    def __iter__(self):
        return iter(self.boundfields)

    @property
    def fields(self):
        return self.boundfields


class Fieldsets:
    def __init__(self, form, fieldsets_data):
        self.form = form
        self.fieldsets = []
        self._dict = {}
        for name, options in fieldsets_data:
            self.add_fieldset(name, options)

    def add_fieldset(self, name, options):
        fields = options.get('fields', [])
        boundfields = [self.form[f] for f in fields if f in self.form.fields]
        classes_opt = options.get('classes', '')
        if isinstance(classes_opt, list | tuple):
            classes_opt = ' '.join(classes_opt)
            
        fieldset = Fieldset(
            form=self.form,
            name=name,
            boundfields=boundfields,
            legend=options.get('legend', name.replace('_', ' ').title() if name else None),
            classes=classes_opt,
            description=options.get('description', ''),
        )
        self.fieldsets.append(fieldset)
        if name:
            self._dict[name] = fieldset

    def __iter__(self):
        return iter(self.fieldsets)

    def __getitem__(self, key):
        return self._dict[key]

    def __getattr__(self, name):
        if name in self._dict:
            return self._dict[name]
        raise AttributeError(f"No fieldset named '{name}'")


class BetterFormMixin:
    """A replacement for django-form-utils BetterForm functionality.
    Provides fieldset support for forms, allowing fields to be grouped into named sections.
    """

    def __init__(self, *args, **kwargs):
        # If we're being initialized directly on a form instance
        if not isinstance(self, BetterFormMixin):
            # Copy our methods to the form instance
            form_instance = args[0] if args else self
            for attr in ['get_fieldsets', 'add_fieldset', 'as_fieldset', '_html_fieldset']:
                method = getattr(BetterFormMixin, attr)
                bound_method = method.__get__(form_instance, form_instance.__class__)
                setattr(form_instance, attr, bound_method)
            return

        super().__init__(*args, **kwargs)
        
        fieldsets_data = getattr(self, 'fieldsets', None)
        if fieldsets_data is None:
            if hasattr(self, 'Meta') and hasattr(self.Meta, 'fieldsets'):
                fieldsets_data = self.Meta.fieldsets
            elif hasattr(self, '_meta') and hasattr(self._meta, 'fieldsets'):
                fieldsets_data = self._meta.fieldsets
                
        if fieldsets_data:
            self.fieldsets = Fieldsets(self, fieldsets_data)
        else:
            self.fieldsets = Fieldsets(self, [(None, {'fields': list(self.fields.keys())})])

    def get_fieldsets(self):
        """Get the fieldsets for this form."""
        if not hasattr(self, 'fieldsets') or not isinstance(self.fieldsets, Fieldsets):
            return []
        return [(fs.name, {'fields': [bf.name for bf in fs.boundfields], 'legend': fs.legend, 'classes': fs.classes, 'description': fs.description}) for fs in self.fieldsets]

    def add_fieldset(self, name, options):
        """Add a fieldset to the form."""
        if not hasattr(self, 'fieldsets') or not isinstance(self.fieldsets, Fieldsets):
            self.fieldsets = Fieldsets(self, [])
        self.fieldsets.add_fieldset(name, options)

    def as_fieldset(self):
        """Render the form as a series of fieldsets."""
        output = []
        if hasattr(self, 'fieldsets') and isinstance(self.fieldsets, Fieldsets):
            for fs in self.fieldsets:
                options = {
                    'fields': [bf.name for bf in fs.boundfields],
                    'legend': fs.legend,
                    'classes': [fs.classes] if fs.classes else [],
                    'description': fs.description,
                }
                output.append(self._html_fieldset(fs.name, options))
        return mark_safe('\n'.join(output))

    def _html_fieldset(self, name, options):
        """Return an individual fieldset as HTML."""
        if name:
            legend = options.get('legend', name)
            classes = ' '.join(options.get('classes', []))
            if classes:
                fieldset_tpl = '<fieldset class="%s">' % classes
            else:
                fieldset_tpl = '<fieldset>'
            output = [fieldset_tpl]
            if legend:
                output.append('<legend>%s</legend>' % legend)
        else:
            output = []

        if options.get('description'):
            output.append('<p class="description">%s</p>' % options['description'])

        for field_name in options['fields']:
            if field_name in getattr(self, 'fields', {}):
                output.append(str(self[field_name]))

        if name:
            output.append('</fieldset>')

        return '\n'.join(output)


class BetterModelForm(BetterFormMixin, forms.ModelForm):
    """A ModelForm subclass that includes fieldset support."""
    pass
