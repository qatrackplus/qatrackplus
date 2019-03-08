import django_filters.widgets as widgets
import rest_framework_filters as filters


class DateFilter(filters.Filter):

    def __init__(self, *args, **kwargs):
        kwargs['widget'] = widgets.forms.DateInput(attrs={'placeholder': 'yyyy-mm-dd', 'type': 'date'})
        super().__init__(*args, **kwargs)


class MinDateFilter(DateFilter):

    def __init__(self, *args, **kwargs):
        kwargs['lookup_expr'] = 'gte'
        super().__init__(*args, **kwargs)


class MaxDateFilter(DateFilter):

    def __init__(self, *args, **kwargs):
        kwargs['lookup_expr'] = 'lte'
        super().__init__(*args, **kwargs)
