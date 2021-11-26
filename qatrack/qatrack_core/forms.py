import json
from django import forms


class MultipleCharField(forms.CharField):
    widget = forms.SelectMultiple

    def to_python(self, value):
        return value


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()


class JSONWidget(forms.widgets.Textarea):
    """To be used in conjunction with qatrack.core.fields.JSONField"""

    def format_value(self, value):
        """Pretty print the Python object ensuring it is stringified in valid
        JSON format"""
        return json.dumps(value, indent=2, sort_keys=True)
