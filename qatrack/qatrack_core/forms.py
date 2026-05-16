from django import forms
from django.utils.safestring import mark_safe


class MultipleCharField(forms.CharField):
    widget = forms.SelectMultiple

    def to_python(self, value):
        return value


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()


class BetterFormMixin:
    """A replacement for django-form-utils BetterForm functionality.
    Provides fieldset support for forms, allowing fields to be grouped into named sections.
    """

    fieldsets = None

    def __init__(self, *args, **kwargs):
        # If we're being initialized directly on a form instance
        if not isinstance(self, BetterFormMixin):
            # Copy our methods to the form instance
            form_instance = args[0] if args else self
            for attr in ["get_fieldsets", "add_fieldset", "as_fieldset", "_html_fieldset"]:
                method = getattr(BetterFormMixin, attr)
                bound_method = method.__get__(form_instance, form_instance.__class__)
                setattr(form_instance, attr, bound_method)
            form_instance._cached_fieldsets = None
            return

        # If we're being used as a mixin, call super().__init__
        super().__init__(*args, **kwargs)
        self._cached_fieldsets = None

    def get_fieldsets(self):
        """Get the fieldsets for this form.

        Returns a list of (name, options) tuples where name is a label for the
        fieldset and options is a dictionary with a 'fields' key mapping to the
        list of field names in the fieldset.
        """
        if self._cached_fieldsets is None:
            self._cached_fieldsets = []
            if hasattr(self, "fieldsets") and self.fieldsets:
                for name, options in self.fieldsets:
                    fields = options.get("fields", ())
                    # Make sure we have access to the form's fields
                    form_fields = getattr(self, "fields", {})
                    filtered_fields = [f for f in fields if f in form_fields]
                    self._cached_fieldsets.append(
                        (
                            name,
                            {
                                "fields": filtered_fields,
                                "legend": options.get("legend", name.replace("_", " ").title() if name else None),
                                "classes": options.get("classes", ()),
                                "description": options.get("description", ""),
                            },
                        )
                    )
            else:
                # Make sure we have access to the form's fields
                form_fields = getattr(self, "fields", {})
                self._cached_fieldsets = [(None, {"fields": list(form_fields.keys())})]
        return self._cached_fieldsets

    def add_fieldset(self, name, options):
        """Add a fieldset to the form.

        Args:
            name: The name/label for the fieldset
            options: Dictionary containing fieldset options (fields, legend, classes, description)
        """
        if self._cached_fieldsets is None:
            self.get_fieldsets()
        self._cached_fieldsets.append((name, options))

    def as_fieldset(self):
        """Render the form as a series of fieldsets."""
        output = []
        for name, options in self.get_fieldsets():
            output.append(self._html_fieldset(name, options))
        return mark_safe("\n".join(output))

    def _html_fieldset(self, name, options):
        """Return an individual fieldset as HTML."""
        if name:
            legend = options.get("legend", name)
            classes = " ".join(options.get("classes", []))
            if classes:
                fieldset_tpl = '<fieldset class="%s">' % classes
            else:
                fieldset_tpl = "<fieldset>"
            output = [fieldset_tpl]
            if legend:
                output.append("<legend>%s</legend>" % legend)
        else:
            output = []

        if options.get("description"):
            output.append('<p class="description">%s</p>' % options["description"])

        for field_name in options["fields"]:
            if field_name in getattr(self, "fields", {}):
                output.append(str(self[field_name]))

        if name:
            output.append("</fieldset>")

        return "\n".join(output)


class BetterModelForm(BetterFormMixin, forms.ModelForm):
    """A ModelForm subclass that includes fieldset support."""

    pass
