from django import forms


class ToolTipSelect(forms.Select):

    def __init__(self, *args, **kwargs):
        self.titles = kwargs.pop('titles', {})
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        options = super(ToolTipSelect, self).create_option(
            name, value, label, selected, index, subindex=None, attrs=None
        )
        for k, v in self.titles.items():
            options['attrs']['title'] = self.titles.get(value, "")

        return options


class DataSelect(forms.Select):

    def __init__(self, attrs=None, choices=(), data=None):
        super().__init__(attrs, choices)
        self.data = data or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)

        for data_attr, values in self.data.items():
            option['attrs'][data_attr] = values[option['value']]

        return option
