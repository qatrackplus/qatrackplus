from braces.views import PermissionRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Count, Max
from django.db.transaction import atomic
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import truncatechars
from django.template.loader import get_template
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, UpdateView
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
from qatrack.service_log import models as sl_models
from qatrack.units.models import Unit


class FaultList(BaseListableView):

    model = models.Fault
    template_name = 'faults/fault_list.html'
    paginate_by = 50

    kwarg_filters = None

    headers = {
        'actions': _l('Actions'),
        'get_id': _l('ID'),
        'get_fault_types': _l("Fault Types"),
        'unit__site__name': _l("Site"),
        'unit__name': _l("Unit"),
        'modality__name': _l("Modality"),
        'get_occurred': _l("Occurred On"),
    }

    widgets = {
        'actions': None,
        'get_id': TEXT,
        'get_fault_types': TEXT,
        'unit__site__name': SELECT_MULTI,
        'unit__name': SELECT_MULTI,
        'modality__name': SELECT_MULTI,
        'get_occurred': DATE_RANGE,
        'review_status': DATE_RANGE,
    }

    search_fields = {
        'actions': False,
        'review_status': 'reviewed',
        'get_fault_types': 'fault_types__code',
        'get_occurred': 'occurred',
        'get_id': 'id',
    }

    order_fields = {
        'actions': False,
        'review_status': 'review_count',
        'get_fault_types': 'fault_types__code',
        'get_occurred': 'occurred',
    }

    date_ranges = {
        "occurred": [TODAY, YESTERDAY, THIS_WEEK, LAST_14_DAYS, THIS_MONTH, THIS_YEAR],
        "review_status": [TODAY, YESTERDAY, THIS_WEEK, LAST_14_DAYS, THIS_MONTH, THIS_YEAR],
    }

    select_related = [
        "unit__site",
        "unit",
        "modality",
        "created_by",
        "modified_by",
    ]

    prefetch_related = [
        "fault_types",
        "faultreviewinstance_set",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Store templates on view initialization so we don't have to reload them for every row!
        self.templates = {
            'actions': get_template('faults/fault_actions.html'),
            'occurred': get_template("faults/fault_occurred.html"),
            'review_status': get_template("faults/fault_review_status.html"),
            'fault_types': get_template("faults/fault_types.html"),
        }

    def get_queryset(self):
        return super().get_queryset().annotate(
            review_count=Max("faultreviewinstance"),
        )

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
            "get_fault_types",
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

    def get_fault_types(self, fault):
        c = {'fault': fault}
        return self.templates['fault_types'].render(c)


class UnreviewedFaultList(FaultList):

    headers = FaultList.headers
    headers["selected"] = mark_safe(
        '<input type="checkbox" class="test-selected-toggle" title="%s"/>' % _("Select All")
    )
    search_fields = FaultList.search_fields
    search_fields["selected"] = False
    order_fields = FaultList.order_fields
    order_fields['selected'] = False

    def get_queryset(self):
        return super().get_queryset().filter(review_count=None)

    def get_fields(self, request=None):
        fields = super().get_fields(request=request)
        if settings.REVIEW_BULK:
            fields += ("selected",)

        return fields

    def selected(self, obj):
        return '<input type="checkbox" class="test-selected" data-fault="%s" title="%s"/>' % (
            obj.id,
            _("Check to include this fault bulk setting approval statuses"),
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['page_title'] = _l("Unreviewed Faults")
        context['bulk_review'] = settings.REVIEW_BULK
        return context


class CreateFault(PermissionRequiredMixin, CreateView):

    model = models.Fault
    template_name = 'faults/fault_form.html'
    form_class = forms.FaultForm

    permission_required = "faults.add_fault"
    raise_exception = True

    @atomic
    def form_valid(self, form):

        context = self.get_context_data()
        reviews_valid = all(f.is_valid() for f in context['review_forms'])
        if not reviews_valid:
            return self.render_to_response(context)

        fault = save_valid_fault_form(form, self.request)
        save_valid_review_forms(context['review_forms'], fault)

        return HttpResponseRedirect(reverse('fault_list'))

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
        context_data['status_tag_colours'] = sl_models.ServiceEventStatus.get_colour_dict()
        if self.request.method == 'POST':
            data_key = "%s-related_service_events" % context_data['form'].prefix
            qs = sl_models.ServiceEvent.objects.filter(pk__in=self.request.POST.getlist(data_key))
            context_data['se_statuses'] = {se.id: se.service_status.id for se in qs}
        else:
            context_data['se_statuses'] = {}

        frgs = models.FaultReviewGroup.objects.order_by("-required", "group__name")
        context_data['review_forms'] = []
        for idx, frg in enumerate(frgs):
            prefix = "review-form-%d" % idx
            data = self.request.POST if self.request.method == "POST" else None
            frg_form = forms.InlineReviewForm(data, fault_review_group=frg, prefix=prefix)
            context_data['review_forms'].append(frg_form)
        return context_data


class EditFault(PermissionRequiredMixin, UpdateView):

    model = models.Fault
    template_name = 'faults/fault_form.html'
    form_class = forms.FaultForm

    permission_required = "faults.change_fault"
    raise_exception = True

    @atomic
    def form_valid(self, form):

        context = self.get_context_data()

        reviews_valid = all(f.is_valid() for f in context['review_forms'])
        if not reviews_valid:
            return self.render_to_response(context)

        fault = save_valid_fault_form(form, self.request)

        reviewed = timezone.now()
        for review_form in context['review_forms']:

            frg = models.FaultReviewGroup.objects.filter(
                group__name=review_form.cleaned_data['group'],
            ).first()

            reviewed_by = review_form.cleaned_data['reviewed_by']

            update_existing_review = review_form.instance is not None
            if update_existing_review:
                reviewer_changed = review_form.instance.reviewed_by != reviewed_by
                if reviewer_changed and not reviewed_by:
                    review_form.instance.delete()
                elif reviewer_changed:
                    review_form.instance.reviewed = reviewed
                    review_form.instance.reviewed_by = reviewed_by
                    review_form.instance.save()
            elif reviewed_by:
                models.FaultReviewInstance.objects.create(
                    reviewed=reviewed,
                    reviewed_by=reviewed_by,
                    fault=fault,
                    fault_review_group=frg,
                )

        return HttpResponseRedirect(reverse('fault_list'))

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
        context_data['status_tag_colours'] = sl_models.ServiceEventStatus.get_colour_dict()
        context_data['se_statuses'] = {}
        if self.request.method == 'POST':
            data_key = "%s-related_service_events" % context_data['form'].prefix
            qs = sl_models.ServiceEvent.objects.filter(pk__in=self.request.POST.getlist(data_key))
            context_data['se_statuses'] = {se.id: se.service_status.id for se in qs}
        elif self.object:
            context_data['se_statuses'] = {
                se.id: se.service_status.id for se in self.object.related_service_events.all()
            }

        frgs = models.FaultReviewGroup.objects.order_by("-required", "group__name")

        # if there are existing reviews we will use those to populate the initial data
        fris = {}
        for fri in self.object.faultreviewinstance_set.exclude(fault_review_group=None):
            fris[fri.fault_review_group.group.name] = fri

        context_data['review_forms'] = []
        for idx, frg in enumerate(frgs):
            data = self.request.POST if self.request.method == "POST" else None
            prefix = "review-form-%d" % idx
            instance = fris.get(frg.group.name)
            frg_form = forms.InlineReviewForm(data, instance=instance, fault_review_group=frg, prefix=prefix)
            context_data['review_forms'].append(frg_form)

        return context_data


class DeleteFault(PermissionRequiredMixin, DeleteView):

    permission_required = "faults.delete_fault"
    raise_exception = True

    model = models.Fault

    def get_success_url(self):
        return self.request.GET.get("next", reverse("fault_list"))

    @atomic
    def delete(self, request, *args, **kwargs):
        Comment.objects.for_model(models.Fault).filter(object_pk=kwargs['pk']).delete()
        res = super().delete(self, request, *args, **kwargs)
        messages.success(request, _("Successfully deleted Fault {fault_id}").format(fault_id=kwargs['pk']))
        return res


def fault_create_ajax(request):
    """Simple view to handle an ajax post of the FaultForm"""

    form = forms.FaultForm(request.POST)

    frgs = models.FaultReviewGroup.objects.order_by("-required", "group__name")
    review_forms = []
    for idx, frg in enumerate(frgs):
        prefix = "review-form-%d" % idx
        frg_form = forms.InlineReviewForm(request.POST, fault_review_group=frg, prefix=prefix)
        review_forms.append(frg_form)

    review_forms_valid = all(f.is_valid() for f in review_forms)

    if form.is_valid() and review_forms_valid:
        fault = save_valid_fault_form(form, request)
        save_valid_review_forms(review_forms, fault)
        fault_id = fault.id
        msg = _("Fault ID %d was created" % fault_id)
    else:
        fault_id = None
        msg = _("Please resolve the errors below and submit again")

    results = {
        'error': fault_id is None,
        'errors': form.errors,
        'review_errors': [f.errors for f in review_forms],
        'message': msg,
    }
    return JsonResponse(results, encoder=QATrackJSONEncoder)


def save_valid_fault_form(form, request):
    """helper for EditFault, CreateFault, and create_ajax for processing FaultForm"""

    fault = form.save(commit=False)

    if not fault.id:
        fault.created_by = request.user

    fault.modified_by = request.user
    fault.save()

    new_faults = set(models.FaultType.objects.filter(code__in=form.cleaned_data['fault_types_field']))
    cur_faults = set(fault.fault_types.all())
    to_remove = cur_faults - new_faults
    to_add = new_faults - cur_faults
    fault.fault_types.remove(*to_remove)
    fault.fault_types.add(*to_add)
    related_service_events = form.cleaned_data.get('related_service_events', [])
    sers = sl_models.ServiceEvent.objects.filter(pk__in=related_service_events)
    fault.related_service_events.set(sers)

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


def save_valid_review_forms(forms, fault):
    reviewed = timezone.now()
    for review_form in forms:
        reviewed_by = review_form.cleaned_data['reviewed_by']
        if not reviewed_by:
            continue

        frg = models.FaultReviewGroup.objects.filter(
            group__name=review_form.cleaned_data['group'],
        ).first()
        models.FaultReviewInstance.objects.create(
            reviewed=reviewed,
            reviewed_by=reviewed_by,
            fault=fault,
            fault_review_group=frg,
        )


def fault_type_autocomplete(request):
    """Look for fault types matching users query.  If the fault type doesn't
    exist, return it as a first option so user can select it and have it
    created when they submit the form."""

    q = request.GET.get('q', '').replace(forms.NEW_FAULT_TYPE_MARKER, "")
    qs = models.FaultType.objects.filter(
        code__icontains=q,
    ).order_by("code")

    qs = qs.values_list("id", "code", "description")

    results = []

    exact_match = None
    for ft_id, code, description in qs:
        description = description or ''
        text = "%s: %s" % (code, truncatechars(description, 80)) if description else code
        if code == q:
            exact_match = (text, description)
        else:
            results.append({'id': code, 'text': text, 'description': description, 'code': code})

    new_option = q and exact_match is None
    if new_option:
        # allow user to create a new match
        new_result = {'id': "%s%s" % (forms.NEW_FAULT_TYPE_MARKER, q), 'text': "*%s*" % q, 'code': q, 'description': ''}
        results = [new_result] + results
    elif q:
        # put the exact match first in the list
        results = [{'id': q, 'code': q, 'text': exact_match[0], 'description': exact_match[1]}] + results

    return JsonResponse({'results': results}, encoder=QATrackJSONEncoder)


class FaultDetails(FaultList):

    template_name = 'faults/fault_details.html'

    def get_queryset(self):
        fault = models.Fault.objects.prefetch_related("fault_types").get(pk=self.kwargs['pk'])
        return super().get_queryset().filter(fault_types__in=fault.fault_types.all())

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        qs = models.Fault.objects.select_related(
            "created_by",
            "modified_by",
        ).prefetch_related(
            "faultreviewinstance_set",
            "fault_types",
        )

        context['fault'] = get_object_or_404(qs, pk=self.kwargs['pk'])

        if models.can_review_faults(self.request.user):
            context['review_form'] = forms.ReviewFaultForm(instance=context['fault'])

        return context


def create_reviews_for_fault(fault, user):

    frgs = models.FaultReviewGroup.objects.filter(group__in=user.groups.all())
    frgs = frgs or [None]
    reviewed = timezone.now()
    reviews = []
    for frg in frgs:
        reviews.append(models.FaultReviewInstance(
            reviewed=reviewed,
            reviewed_by=user,
            fault=fault,
            fault_review_group=frg,
        ))
    return reviews


@require_POST
def review_fault(request, pk):
    fault = get_object_or_404(models.Fault.objects.all(), pk=pk)
    form = forms.ReviewFaultForm(request.POST, instance=fault)
    if form.is_valid():
        fault = form.save(commit=False)
        fault.modified_by = request.user
        fault.save()
        approve = fault.faultreviewinstance_set.first() is None
        if approve:
            reviews = create_reviews_for_fault(fault, request.user)
            for review in reviews:
                review.save()
        else:
            fault.faultreviewinstance_set.all().delete()

        if approve:
            messages.success(request, _("Successfully approved %(fault)s ") % {'fault': fault})
        else:
            messages.warning(request, _("Successfully unapproved %(fault)s ") % {'fault': fault})
    else:  # pragma: nocover
        messages.error(_("Sorry, something went wrong trying to review this fault. It has not been updated"))

    return HttpResponseRedirect(reverse('fault_details', kwargs={'pk': fault.pk}))


@require_POST
@atomic
def bulk_review(request):
    faults = request.POST.getlist('faults')
    faults = models.Fault.objects.unreviewed().filter(pk__in=faults)

    to_create = []
    for f in faults:
        reviews = create_reviews_for_fault(f, request.user)
        to_create.extend(reviews)
    models.FaultReviewInstance.objects.bulk_create(to_create)

    count = len(to_create)
    msg = _("Successfully reviewed %(count)s faults") % {'count': count}
    messages.add_message(request=request, message=msg, level=messages.SUCCESS)
    return JsonResponse({"ok": True})


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
        exclude = ['unit__site__name', 'unit__name', 'fault_types']
        fields = super().get_fields(request)
        return [f for f in fields if f not in exclude]

    def get_queryset(self):
        return super().get_queryset().filter(
            unit__number=self.kwargs['unit_number'],
            fault_types__slug=self.kwargs['slug'],
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
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.templates = {
            'actions': get_template('faults/fault_type_actions.html'),
            'description': get_template("faults/fault_type_description.html"),
        }

    def get_queryset(self):
        return super().get_queryset().order_by("code").annotate(
            count=Count("faults"),
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
            fault_types__slug=self.kwargs['slug'],
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        fault_type = get_object_or_404(models.FaultType, slug=self.kwargs['slug'])
        unit_faults = models.Fault.objects.filter(
            fault_types=fault_type,
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
