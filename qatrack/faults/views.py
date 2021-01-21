from braces.views import LoginRequiredMixin
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Count
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import CreateView, UpdateView
from django_comments.models import Comment
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

from qatrack.faults import forms, models
from qatrack.qa.views.perform import ChooseUnit
from qatrack.qatrack_core.serializers import QATrackJSONEncoder
from qatrack.units.models import Unit


class FaultList(BaseListableView):

    model = models.Fault
    template_name = 'faults/fault_list.html'
    paginate_by = 50

    kwarg_filters = None

    headers = {
        'actions': _l('Actions'),
        'get_id': _l('ID'),
        'get_fault_type': _l("Fault Type"),
        'unit__site__name': _l("Site"),
        'unit__name': _l("Unit"),
        'modality__name': _l("Modality"),
        'treatment_technique__name': _l("Technique"),
        'get_occurred': _l("Occurred On"),
    }

    widgets = {
        'actions': None,
        'get_id': TEXT,
        'get_fault_type': TEXT,
        'unit__site__name': SELECT_MULTI,
        'unit__name': SELECT_MULTI,
        'modality__name': SELECT_MULTI,
        'treatment_technique__name': SELECT_MULTI,
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
        'get_fault_type': 'fault_type',
        'get_occurred': 'occurred',
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
        "treatment_technique",
        "reviewed_by",
        "created_by",
        "modified_by",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Store templates on view initialization so we don't have to reload them for every row!
        self.templates = {
            'actions': get_template('faults/fault_actions.html'),
            'occurred': get_template("faults/fault_occurred.html"),
            'review_status': get_template("faults/fault_review_status.html"),
            'fault_type': get_template("faults/fault_type.html"),
        }

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['icon'] = 'fa-exclamation-triangle'
        context['view_name'] = current_url
        context['page_title'] = _l("All Faults")
        return context

    def get_fields(self, request=None):

        fields = (
            "actions",
            "id",
            "get_occurred",
            "get_fault_type",
        )

        multiple_sites = len(set(Unit.objects.values_list("site_id"))) > 1
        if multiple_sites:
            fields += ("unit__site__name",)

        fields += (
            "unit__name",
            "modality__name",
            "treatment_technique__name",
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
            'next': reverse('fault_list'),
            'perms': PermWrapper(self.request.user),
        }
        return self.templates['actions'].render(c)

    def review_status(self, fault):
        c = {'fault': fault}
        return self.templates['review_status'].render(c)

    def get_occurred(self, fault):
        c = {'fault': fault}
        return self.templates['occurred'].render(c)

    def get_fault_type(self, fault):
        c = {'fault': fault}
        return self.templates['fault_type'].render(c)


class CreateFault(LoginRequiredMixin, CreateView):

    model = models.Fault
    template_name = 'faults/fault_form.html'
    form_class = forms.FaultForm

    def form_valid(self, form):
        save_valid_fault_form(form, self.request)
        return HttpResponseRedirect(reverse('fault_list'))


class EditFault(LoginRequiredMixin, UpdateView):

    model = models.Fault
    template_name = 'faults/fault_form.html'
    form_class = forms.FaultForm

    def form_valid(self, form):
        save_valid_fault_form(form, self.request)
        return HttpResponseRedirect(reverse('fault_list'))


def fault_create_ajax(request):
    """Simple view to handle an ajax post of the FaultForm"""

    form = forms.FaultForm(request.POST)

    if form.is_valid():
        fault = save_valid_fault_form(form, request)
        fault_id = fault.id
        msg = _("Fault ID %d was created" % fault_id)
    else:
        fault_id = None
        msg = _("Please resolve the errors below and submit again")

    results = {
        'error': fault_id is None,
        'errors': form.errors,
        'message': msg,
    }
    return JsonResponse(results, encoder=QATrackJSONEncoder)


def save_valid_fault_form(form, request):
    """helper for EditFault, CreateFault, and create_ajax for processing FaultForm"""

    fault = form.save(commit=False)
    fault.fault_type = models.FaultType.objects.get(code=form.cleaned_data['fault_type_field'])
    if not fault.id:
        fault.created_by = request.user
    fault.modified_by = request.user
    fault.save()

    comment = form.cleaned_data.get('comment', '')
    if comment:
        comment = Comment(
            submit_date=timezone.now(),
            user=request.user,
            content_object=fault,
            comment=comment,
            site=get_current_site(request)
        )
        comment.save()

    return fault


def fault_type_autocomplete(request):
    """Look for fault types matching users query.  If the fault type doesn't
    exist, return it as a first option so user can select it and have it
    created when they submit the form."""

    q = request.GET.get('q', '')

    qs = models.FaultType.objects.filter(
        code__icontains=q,
    ).order_by("code").values_list("id", "code")

    results = []

    exact_match = -1
    for ft_id, code in qs:
        if code == q:
            exact_match = ft_id
        else:
            results.append({'id': code, 'text': code})

    new_option = q and (exact_match < 0)
    if new_option:
        # allow user to create a new match
        results = [{'id': "%s%s" % (forms.NEW_FAULT_TYPE_MARKER, q), 'text': "*%s*" % q}] + results
    elif q:
        # put the exact match first in the list
        results = [{'id': q, 'text': q}] + results

    return JsonResponse({'results': results}, encoder=QATrackJSONEncoder)


class FaultDetails(FaultList):

    model = models.Fault
    template_name = 'faults/fault_details.html'

    def get_queryset(self):
        fault = models.Fault.objects.select_related("fault_type").get(pk=self.kwargs['pk'])
        return super().get_queryset().filter(fault_type=fault.fault_type)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        qs = models.Fault.objects.select_related(
            "created_by",
            "modified_by",
            "reviewed_by",
            "fault_type",
        )
        context['fault'] = get_object_or_404(qs, pk=self.kwargs['pk'])
        return context


class FaultsByUnit(FaultList):

    model = models.Fault
    template_name = 'faults/fault_list.html'

    def get_fields(self, request):
        exclude = ['unit__site__name', 'unit__name']
        fields = super().get_fields(request)
        return [f for f in fields if f not in exclude]

    def get_queryset(self):
        return super().get_queryset().filter(unit__number=self.kwargs['unit_number'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        unit = get_object_or_404(Unit, number=self.kwargs['unit_number'])
        context['unit'] = unit
        context['page_title'] = "%s: %s" % (_("Faults for"), unit.site_unit_name())
        return context


class FaultsByUnitFaultType(FaultList):

    model = models.Fault
    template_name = 'faults/fault_list.html'

    def get_fields(self, request):
        exclude = ['unit__site__name', 'unit__name', 'fault_type']
        fields = super().get_fields(request)
        return [f for f in fields if f not in exclude]

    def get_queryset(self):
        return super().get_queryset().filter(
            unit__number=self.kwargs['unit_number'],
            fault_type__slug=self.kwargs['slug'],
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        unit = get_object_or_404(Unit, number=self.kwargs['unit_number'])
        fault_type = get_object_or_404(models.FaultType, slug=self.kwargs['slug'])
        context['unit'] = unit
        context['fault_type'] = fault_type
        title = _("{fault_type} faults for: {site_and_unit_name}").format(
            fault_type=fault_type,
            site_and_unit_name=unit.site_unit_name(),
        )
        context['page_title'] = title
        return context


class FaultTypeList(BaseListableView):

    model = models.FaultType
    template_name = 'faults/fault_type_list.html'
    paginate_by = 50

    kwarg_filters = None

    fields = (
        "actions",
        "code",
        'count',
        "description",
    )

    headers = {
        'actions': _l('Actions'),
        'code': _l('Fault Type'),
        'count': _l("# of Occurrences"),
        'description': _l("Description"),
    }

    widgets = {
        'actions': None,
        'code': TEXT,
        'count': None,
        'description': TEXT,
    }

    search_fields = {
        'actions': False,
        'count': None,
    }

    order_fields = {
        'actions': False,
        'description': False,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.templates = {
            'actions': get_template('faults/fault_type_actions.html'),
            'description': get_template("faults/fault_type_description.html"),
        }

    def get_queryset(self):
        return super().get_queryset().annotate(
            count=Count("fault"),
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['page_title'] = _l("All Fault Types")
        return context

    def actions(self, fault_type):
        c = {
            'fault_type': fault_type,
            'next': reverse('fault_type_list'),
            'perms': PermWrapper(self.request.user),
        }
        return self.templates['actions'].render(c)

    def description(self, fault_type):
        c = {'fault_type': fault_type}
        return self.templates['description'].render(c)


class FaultTypeDetails(FaultList):

    template_name = 'faults/fault_type_details.html'

    def get_queryset(self):
        return super().get_queryset().filter(
            fault_type__slug=self.kwargs['slug'],
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        fault_type = get_object_or_404(models.FaultType, slug=self.kwargs['slug'])
        unit_faults = models.Fault.objects.filter(
            fault_type=fault_type,
        ).values(
            "unit__name",
            "unit__number",
            "unit_id",
        ).annotate(
            unit_count=Count("unit__%s" % settings.ORDER_UNITS_BY)
        ).order_by(
            "-unit_count",
        )
        context['fault_type'] = fault_type
        context['unit_faults'] = unit_faults

        return context


class ChooseUnitForViewFaults(ChooseUnit):
    template_name = 'units/unittype_choose_for_faults.html'
    split_sites = True
