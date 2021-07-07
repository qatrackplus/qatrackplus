from django import forms


class MultipleCharField(forms.CharField):
    widget = forms.SelectMultiple

    def to_python(self, value):
        return value


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()
