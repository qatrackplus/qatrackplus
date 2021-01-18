from django.contrib.auth.context_processors import PermWrapper
from django.template.loader import get_template
from django.urls import resolve, reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import DetailView
from listable.views import (
    DATE_RANGE,
    LAST_14_DAYS,
    NONEORNULL,
    SELECT_MULTI,
    TEXT,
    THIS_MONTH,
    THIS_WEEK,
    THIS_YEAR,
    TODAY,
    YESTERDAY,
    BaseListableView,
)

from qatrack.faults import models
from qatrack.units.models import Unit


class FaultList(BaseListableView):

    model = models.Fault
    template_name = 'faults/faults_list.html'
    paginate_by = 50

    kwarg_filters = None

    headers = {
        'actions': _l('Actions'),
        'get_id': _l('ID'),
        'unit__site__name': _l("Site"),
        'unit__name': _l("Unit"),
        'modality__name': _l("Modality"),
        'get_occurred': _l("Occurred On"),
    }

    widgets = {
        'actions': None,
        'get_id': TEXT,
        'fault_type': SELECT_MULTI,
        'unit__site__name': SELECT_MULTI,
        'unit__name': SELECT_MULTI,
        'modality__name': SELECT_MULTI,
        'get_occurred': DATE_RANGE,
        'review_status': DATE_RANGE,
    }

    search_fields = {
        'actions': False,
        'review_status': 'reviewed',
    }

    order_fields = {
        'actions': False,
        'review_status': 'reviewed',
    }

    date_ranges = {
        "occurred": [TODAY, YESTERDAY, THIS_WEEK, LAST_14_DAYS, THIS_MONTH, THIS_YEAR],
        "review_status": [TODAY, YESTERDAY, THIS_WEEK, LAST_14_DAYS, THIS_MONTH, THIS_YEAR],
    }

    select_related = [
        "fault_type",
        "unit__site",
        "unit",
        "modality",
        "reviewed_by",
        "created_by",
        "modified_by",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Store templates on view initialization so we don't have to reload them for every row!
        self.templates = {
            'actions': get_template('faults/faults_actions.html'),
            'occurred': get_template("faults/fault_occurred.html"),
            'review_status': get_template("faults/fault_review_status.html"),
        }

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['page_title'] = _l("All Faults")
        return context

    def get_fields(self, request=None):

        fields = (
            "actions",
            "id",
            "get_occurred",
            "fault_type",
        )

        multiple_sites = len(set(Unit.objects.values_list("site_id"))) > 1
        if multiple_sites:
            fields += ("unit__site__name",)

        fields += (
            "unit__name",
            "modality__name",
            "review_status",
        )
        return fields

    def get_filters(self, field, queryset=None):

        filters = super().get_filters(field, queryset=queryset)

        if field == 'unit__site__name':
            filters = [(NONEORNULL, _("Other")) if f == (NONEORNULL, 'None') else f for f in filters]

        return filters

    def actions(self, fault):
        c = {
            'fault': fault,
            'next': reverse('fault'),
            'perms': PermWrapper(self.request.user),
        }
        return self.templates['actions'].render(c)

    def review_status(self, fault):
        c = {'fault': fault}
        return self.templates['review_status'].render(c)

    def get_occurred(self, fault):
        c = {'fault': fault}
        return self.templates['occurred'].render(c)


class EditFault(DetailView):

    model = models.Fault
    template_name = 'faults/fault_edit.html'


class FaultDetails(DetailView):

    model = models.Fault
    template_name = 'faults/fault_details.html'
