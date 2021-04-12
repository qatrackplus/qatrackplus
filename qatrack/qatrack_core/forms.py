from django import forms


class MultipleCharField(forms.CharField):
    widget = forms.SelectMultiple

    def to_python(self, value):
        return value
