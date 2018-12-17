from collections import OrderedDict
import csv

from braces.views import LoginRequiredMixin, PermissionRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import resolve, reverse
from django.db.models import Sum
from django.forms.utils import timezone
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.generic import DeleteView, DetailView, FormView, TemplateView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView
from django_comments.models import Comment
from listable.views import (
    DATE_RANGE,
    LAST_7_DAYS,
    LAST_30_DAYS,
    LAST_365_DAYS,
    LAST_MONTH,
    LAST_WEEK,
    LAST_YEAR,
    SELECT,
    SELECT_MULTI,
    THIS_MONTH,
    THIS_WEEK,
    THIS_YEAR,
    TODAY,
    YEAR_TO_DATE,
    YESTERDAY,
    BaseListableView,
)

from qatrack.attachments.models import Attachment
from qatrack.qa import models as qa_models
from qatrack.qa.templatetags import qa_tags
from qatrack.qa.views.base import generate_review_status_context
from qatrack.qa.views.perform import ChooseUnit
from qatrack.qa.views.review import UTCInstances
from qatrack.service_log import forms, models
from qatrack.units import models as u_models

if settings.USE_PARTS:
    from qatrack.parts import forms as p_forms
    from qatrack.parts import models as p_models


def get_time_display(dt):

    if not isinstance(dt, timezone.datetime):
        raise ValueError('%s is not a valid datetime' % dt)
    if timezone.now() - dt < timezone.timedelta(hours=1):
        ago = timezone.now() - dt
        # ago = timezone.timedelta(minutes=ago.minute)
        return str(ago.seconds // 60) + ' minutes ago'
    else:
        return dt.strftime('%I:%M %p')


def unit_sa_utc(request):

    try:
        unit = models.Unit.objects.get(id=request.GET['unit_id'])
    except (KeyError, ObjectDoesNotExist):
        raise Http404
    service_areas = list(models.ServiceArea.objects.filter(units=unit).values())

    utcs_tl_qs = models.UnitTestCollection.objects.select_related('frequency').filter(unit=unit, active=True)
    utcs_tl = sorted(
        [
            {'id': utc.id, 'name': utc.name, 'frequency': utc.frequency.name if utc.frequency else 'Ad Hoc'}
            for utc in utcs_tl_qs
        ],
        key=lambda utc: utc['name']
    )
    return JsonResponse({'service_areas': service_areas, 'utcs': utcs_tl})


def se_searcher(request):

    try:
        se_search = request.GET['q']
        unit_id = request.GET['unit_id']
    except KeyError:
        return JsonResponse({'error': True}, status=404)

    omit_id = request.GET.get('self_id', 'false')
    service_events = models.ServiceEvent.objects \
        .filter(id__icontains=se_search, unit_service_area__unit=unit_id)

    if omit_id != 'false':
        service_events = service_events.exclude(id=omit_id)

    service_events = service_events.order_by('-id') \
        .select_related('service_status')[0:50]\
        .values_list('id', 'service_status__id', 'problem_description', 'datetime_service', 'service_status__name')

    return JsonResponse({'service_events': list(service_events)})


class SLDashboard(TemplateView):

    template_name = "service_log/sl_dash.html"

    def get_counts(self):

        rtsqa_qs = models.ReturnToServiceQA.objects.prefetch_related().all()
        default_status = models.ServiceEventStatus.objects.get(is_default=True)
        to_return = {
            'qa_not_reviewed': rtsqa_qs.filter(test_list_instance__isnull=False, test_list_instance__all_reviewed=False).count(),
            'qa_not_complete': rtsqa_qs.filter(test_list_instance__isnull=True).count(),
            'se_needing_review': models.ServiceEvent.objects.filter(
                service_status__in=models.ServiceEventStatus.objects.filter(
                    is_review_required=True
                ),
                is_review_required=True
            ).count(),
            'se_default': {
                'status_name': default_status.name,
                'id': default_status.id,
                'count': models.ServiceEvent.objects.filter(service_status=default_status).count()
            }
        }
        return to_return

    def get_context_data(self, **kwargs):

        context = super(SLDashboard, self).get_context_data()
        context['counts'] = self.get_counts()
        context['recent_logs'] = models.ServiceLog.objects.select_related(
            'user', 'service_event', 'service_event__unit_service_area__unit'
        )[:60]

        return context

    def dispatch(self, request, *args, **kwargs):
        if models.ServiceEventStatus.objects.filter(is_default=True).exists():
            return super(SLDashboard, self).dispatch(request, *args, **kwargs)
        else:
            return redirect(reverse('err'))


class ErrorView(TemplateView):

    template_name = 'service_log/error_base.html'


class ServiceEventUpdateCreate(LoginRequiredMixin, PermissionRequiredMixin, SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    """
    CreateView and UpdateView functionality combined
    """
    permission_required = 'service_log.add_serviceevent'
    raise_exception = True
    model = models.ServiceEvent
    template_name = 'service_log/service_event_update.html'
    form_class = forms.ServiceEventForm

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super(ServiceEventUpdateCreate, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.

        By default this requires `self.queryset` and a `pk` or `slug` argument
        in the URLconf, but subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if pk is not None:
            queryset = queryset.filter(pk=pk).select_related(
                'test_list_instance_initiated_by',
            ).prefetch_related(
                'returntoserviceqa_set',
                'test_list_instance_initiated_by__testinstance_set',
                'test_list_instance_initiated_by__testinstance_set__status',
                'test_list_instance_initiated_by__unit_test_collection__tests_object'
            )

        # If none of those are defined, it's an error.
        if pk is None and slug is None:
            return None

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(ServiceEventUpdateCreate, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(ServiceEventUpdateCreate, self).post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ServiceEventUpdateCreate, self).get_form_kwargs()
        # group_linkers = models.GroupLinker.objects.all()
        kwargs['group_linkers'] = models.GroupLinker.objects.all()
        kwargs['user'] = self.user
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context_data = super(ServiceEventUpdateCreate, self).get_context_data(**kwargs)

        self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        if self.request.method == 'POST':
            qs = models.ServiceEvent.objects.filter(pk__in=self.request.POST.getlist('service_event_related_field'))
            context_data['se_statuses'] = {se.id: se.service_status.id for se in qs}
        elif self.object:
            context_data['se_statuses'] = {se.id: se.service_status.id for se in self.object.service_event_related.all()}
        else:
            context_data['se_statuses'] = {}
        context_data['status_tag_colours'] = models.ServiceEventStatus.get_colour_dict()
        context_data['se_types_review'] = {st.id: int(st.is_review_required) for st in models.ServiceType.objects.all()}

        context_data['ses_status_details'] = {
            ses.id: {
                'is_review_required': int(ses.is_review_required),
                'rts_qa_must_be_reviewed': int(ses.rts_qa_must_be_reviewed),
                'is_default': int(ses.is_default)
            } for ses in models.ServiceEventStatus.objects.all()
        }
        context_data['default_qa_status_name'] = qa_models.TestInstanceStatus.objects.filter(is_default=True).first().name

        unit_field = self.object.unit_service_area.unit if self.object is not None else None
        if not unit_field:
            try:
                if self.request.GET.get('ib'):
                    unit_field = qa_models.TestListInstance.objects.get(
                        pk=self.request.GET.get('ib')).unit_test_collection.unit
                elif self.request.GET.get('u'):
                    unit_field = u_models.Unit.objects.get(pk=self.request.GET.get('u'))
            except ObjectDoesNotExist:
                pass

        extra_rtsqa_forms = 2 if self.request.user.has_perm('service_log.add_returntoserviceqa') else 0
        if self.request.method == 'POST':

            context_data['hours_formset'] = forms.HoursFormset(
                self.request.POST,
                instance=self.object,
                prefix='hours'
            )
            context_data['rtsqa_formset'] = forms.get_rtsqa_formset(extra_rtsqa_forms)(
                self.request.POST,
                instance=self.object,
                prefix='rtsqa',
                form_kwargs={
                    'service_event_instance': self.object,
                    'unit_field': unit_field,
                    'user': self.request.user
                },
                queryset=models.ReturnToServiceQA.objects.filter(service_event=self.object).select_related(
                    'test_list_instance',
                    'test_list_instance__test_list',
                    'unit_test_collection',
                    'user_assigned_by'
                ).prefetch_related(
                    "test_list_instance__testinstance_set",
                    "test_list_instance__testinstance_set__status",
                    'unit_test_collection__tests_object'
                )
            )
            if settings.USE_PARTS:
                context_data['part_used_formset'] = p_forms.PartUsedFormset(
                    self.request.POST,
                    instance=self.object,
                    prefix='parts'
                )
        else:

            context_data['hours_formset'] = forms.HoursFormset(instance=self.object, prefix='hours')
            context_data['rtsqa_formset'] = forms.get_rtsqa_formset(extra_rtsqa_forms)(
                instance=self.object,
                prefix='rtsqa',
                form_kwargs={
                    'service_event_instance': self.object,
                    'unit_field': unit_field,
                    'user': self.request.user
                },
                queryset=models.ReturnToServiceQA.objects.filter(service_event=self.object).select_related(
                    'test_list_instance',
                    'test_list_instance__test_list',
                    'unit_test_collection',
                    'user_assigned_by'
                ).prefetch_related(
                    "test_list_instance__testinstance_set",
                    "test_list_instance__testinstance_set__status",
                    'unit_test_collection__tests_object'
                )
            )
            if settings.USE_PARTS:
                context_data['part_used_formset'] = p_forms.PartUsedFormset(instance=self.object, prefix='parts')

        context_data['attachments'] = self.object.attachment_set.all() if self.object else []

        if self.request.GET.get('next'):
            context_data['next_url'] = self.request.GET.get('next')
        return context_data

    def form_invalid(self, form):
        messages.add_message(self.request, messages.ERROR, _('Please correct the error below.'))
        return super().form_invalid(form)

    def reset_status(self, form):

        if not form.instance.service_status.is_review_required:
            default = models.ServiceEventStatus.get_default()
            form.instance.service_status = default
            messages.add_message(self.request, messages.WARNING, _(
                'Due to changes detected, service event %s status has been reset to %s' % (
                    form.instance.id, default.name.lower()
                )
            ))
            form.changed_data.append('service_status')
            form.cleaned_data['service_status'] = default

    def edit_se_attachments(self, service_event):
        for idx, f in enumerate(self.request.FILES.getlist('se_attachments')):
            Attachment.objects.create(
                attachment=f,
                comment="Uploaded %s by %s" % (timezone.now(), self.request.user.username),
                label=f.name,
                serviceevent=service_event,
                created_by=self.request.user
            )

        a_ids = self.request.POST.get('se_attachments_delete_ids', '').split(',')
        if a_ids != ['']:
            Attachment.objects.filter(id__in=a_ids).delete()

    def form_valid(self, form):

        context = self.get_context_data()
        hours_formset = context["hours_formset"]
        rtsqa_formset = context["rtsqa_formset"]

        if settings.USE_PARTS:
            parts_formset = context['part_used_formset']
            if not parts_formset or not parts_formset.is_valid():
                messages.add_message(self.request, messages.ERROR, _('Please correct the error below.'))
                return self.render_to_response(context)
        else:
            parts_formset = None

        if not hours_formset.is_valid() or not rtsqa_formset.is_valid():
            messages.add_message(self.request, messages.ERROR, _('Please correct the error below.'))
            return self.render_to_response(context)

        new = form.instance.pk is None

        service_event = form.save()
        service_event_related = form.cleaned_data.get('service_event_related_field')
        try:
            sers = models.ServiceEvent.objects.filter(pk__in=service_event_related)
        except ValueError:
            sers = []
        service_event.service_event_related.set(sers)

        if 'service_status' in form.changed_data:
            se_needing_review_count = models.ServiceEvent.objects.filter(
                service_status__in=models.ServiceEventStatus.objects.filter(is_review_required=True),
                is_review_required=True
            ).count()
            cache.set('se_needing_review_count', se_needing_review_count)

        comment = form.cleaned_data['qafollowup_comments']
        if comment:
            comment = Comment(
                submit_date=timezone.now(),
                user=self.request.user,
                content_object=service_event,
                comment=comment,
                site=get_current_site(self.request)
            )
            comment.save()

        for g_link in form.g_link_dict:
            if g_link in form.changed_data:

                try:
                    gl_instance = models.GroupLinkerInstance.objects.get(
                        service_event=service_event, group_linker=form.g_link_dict[g_link]['g_link']
                    )
                    gl_instance.user = form.cleaned_data[g_link]
                    gl_instance.datetime_linked = timezone.now()
                except ObjectDoesNotExist:
                    gl_instance = models.GroupLinkerInstance(
                        service_event=service_event,
                        group_linker=form.g_link_dict[g_link]['g_link'],
                        user=form.cleaned_data[g_link],
                        datetime_linked=timezone.now()
                    )
                if form.cleaned_data[g_link] is None:
                    gl_instance.delete()
                else:
                    gl_instance.save()

        for h_form in hours_formset:

            user_or_thirdparty = h_form.cleaned_data.get('user_or_thirdparty')
            delete = h_form.cleaned_data.get('DELETE')
            is_new = h_form.instance.id is None

            h_instance = h_form.instance

            if delete and not is_new:
                h_instance.delete()
                continue

            elif h_form.has_changed():

                if isinstance(user_or_thirdparty, User):
                    user = user_or_thirdparty
                    third_party = None
                else:
                    third_party = user_or_thirdparty
                    user = None

                h_instance.service_event = service_event
                h_instance.user = user
                h_instance.third_party = third_party
                h_instance.time = h_form.cleaned_data.get('time', '')

                h_instance.save()

        for f_form in rtsqa_formset:

            delete = f_form.cleaned_data.get('DELETE')
            is_new = f_form.instance.id is None

            f_instance = f_form.instance

            if delete and not is_new:
                f_instance.delete()
                continue

            elif f_form.has_changed():

                if is_new:
                    f_instance.user_assigned_by = self.request.user
                    f_instance.datetime_assigned = timezone.now()
                    f_instance.service_event = service_event
                f_instance.save()

        if settings.USE_PARTS:

            for p_form in parts_formset:

                if not p_form.has_changed():
                    continue

                delete = p_form.cleaned_data.get('DELETE')
                is_new = p_form.instance.id is None

                pu_instance = p_form.instance

                initial_p = p_form.initial.get('part', None)
                if delete:
                    current_p = p_form.initial['part']
                else:
                    current_p = p_form.cleaned_data['part']

                initial_s = p_form.initial.get('from_storage', None)
                current_s = p_form.cleaned_data.get('from_storage', None)

                try:
                    current_psc = p_models.PartStorageCollection.objects.get(
                        part=current_p, storage=current_s
                    ) if current_s else None
                except ObjectDoesNotExist:
                    current_psc = p_models.PartStorageCollection(
                        part=current_p, storage=current_s, quantity=0
                    )
                try:
                    initial_psc = p_models.PartStorageCollection.objects.get(
                        part=initial_p, storage=initial_s
                    ) if initial_s and initial_p else None
                except ObjectDoesNotExist:
                    initial_psc = None

                initial_qty = 0 if is_new else p_form.initial['quantity']
                current_qty = p_form.cleaned_data.get('quantity', initial_qty)
                change = current_qty - initial_qty

                if delete and not is_new:
                    if current_psc:
                        qty = pu_instance.quantity
                        current_psc.quantity += qty

                        if current_psc:
                            current_psc.save()

                        if initial_psc:
                            initial_psc.save()

                    pu_instance.delete()
                    continue

                elif p_form.has_changed():

                    if is_new:
                        pu_instance.service_event = service_event

                    # If parts storage changed
                    if 'from_storage' in p_form.changed_data:

                        if initial_psc:
                            initial_psc.quantity += initial_qty
                            initial_psc.save()
                        if current_psc:
                            current_psc.quantity -= current_qty
                            current_psc.save()
                        pu_instance.from_storage = current_psc.storage if current_psc else None

                    # Edge case if part changed and storage didn't
                    elif 'part' in p_form.changed_data and current_psc:

                        if initial_s:
                            if not initial_psc and change < 0:
                                initial_psc = p_models.PartStorageCollection(
                                    part=initial_p,
                                    storage=initial_s,
                                    quantity=-change
                                )
                                current_psc.save()
                            initial_psc.quantity += initial_qty
                            initial_psc.save()

                        current_psc.quantity -= current_qty
                        current_psc.save()

                    # Else if just quantity changed
                    elif 'quantity' in p_form.changed_data:

                        if current_psc:
                            current_psc.quantity -= change
                            current_psc.save()
                        # If trying to put a part back to storage with no part storage collection
                        elif current_s and change < 0:
                            current_psc = p_models.PartStorageCollection(
                                part=current_p,
                                storage=current_s,
                                quantity=-change
                            )
                            current_psc.save()

                    pu_instance.save()
                    if current_p.set_quantity_current():
                        messages.add_message(
                            request=self.request,
                            level=messages.INFO,
                            message='Part number %s is low (%s left in stock).' % (current_p.part_number, current_p.quantity_current)
                        )
                    if initial_p:
                        initial_p.set_quantity_current()

        self.generate_logs(new, form, rtsqa_formset)
        self.edit_se_attachments(service_event)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        return reverse("sl_dash")

    def generate_logs(self, is_new, form, rtsqa_formset):

        if is_new:
            models.ServiceLog.objects.log_new_service_event(self.request.user, form.instance)

        elif 'service_status' in form.changed_data:
            models.ServiceLog.objects.log_service_event_status(
                self.request.user, form.instance, form.stringify_form_changes(self.request), form.stringify_status_change()
            )

        elif form.has_changed():
            models.ServiceLog.objects.log_changed_service_event(
                self.request.user, form.instance, form.stringify_form_changes(self.request)
            )

        if rtsqa_formset.has_changed():
            models.ServiceLog.objects.log_rtsqa_changes(
                self.request.user, models.ServiceEvent.objects.get(pk=form.instance.pk)
            )


class CreateServiceEvent(ServiceEventUpdateCreate):

    def get_form_kwargs(self):
        kwargs = super(CreateServiceEvent, self).get_form_kwargs()
        kwargs['initial_ib'] = self.request.GET.get('ib', None)
        kwargs['initial_u'] = self.request.GET.get('u', None)
        return kwargs

    def form_valid(self, form):

        self.instance = form.save(commit=False)
        form.instance.user_created_by = self.request.user
        form.instance.datetime_created = timezone.now()

        if not form.cleaned_data['service_status'].id == models.ServiceEventStatus.get_default().id:
            form.instance.datetime_status_changed = timezone.now()
            form.instance.user_status_changed_by = self.request.user

        form_valid = super(CreateServiceEvent, self).form_valid(form)

        return form_valid


class UpdateServiceEvent(ServiceEventUpdateCreate):

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['service_logs'] = models.ServiceLog.objects.filter(service_event=self.object)
        return context

    def form_valid(self, form):

        self.instance = form.save(commit=False)

        if 'is_review_required_fake' in form.changed_data:
            form.changed_data.remove('is_review_required_fake')

        if 'unit_field_fake' in form.changed_data:
            form.changed_data.remove('unit_field_fake')

        if 'service_status' in form.changed_data:
            form.instance.datetime_status_changed = timezone.now()
            form.instance.user_status_changed_by = self.request.user

            # Only change modified fields if service_status was not the only changed field
            if len(form.changed_data) > 1:
                form.instance.user_modified_by = self.request.user
                form.instance.datetime_modified = timezone.now()

        elif len(form.changed_data) > 0:
            form.instance.user_modified_by = self.request.user
            form.instance.datetime_modified = timezone.now()

            # Check if service status was not changed explicitly, but needs to be reset to default status due to other changes.
            self.reset_status(form)

        return super(UpdateServiceEvent, self).form_valid(form)


class DetailsServiceEvent(DetailView):

    model = models.ServiceEvent
    template_name = 'service_log/service_event_detail.html'

    def get_context_data(self, **kwargs):
        context_data = super(DetailsServiceEvent, self).get_context_data(**kwargs)
        # context_data['service_event_tag_colours'] = models.ServiceEvent.get_colour_dict()
        context_data['hours'] = models.Hours.objects.filter(service_event=self.object)
        context_data['rtsqas'] = models.ReturnToServiceQA.objects.filter(service_event=self.object).select_related(
            'test_list_instance',
            'test_list_instance__test_list',
            'unit_test_collection',
            'user_assigned_by'
        ).prefetch_related(
            "test_list_instance__testinstance_set",
            "test_list_instance__testinstance_set__status",
            'unit_test_collection__tests_object'
        )
        context_data['parts_used'] = p_models.PartUsed.objects.filter(service_event=self.object)
        context_data['request'] = self.request
        context_data['g_links'] = models.GroupLinkerInstance.objects.filter(service_event=self.object)

        context_data['service_logs'] = models.ServiceLog.objects.filter(service_event=self.object)

        return context_data

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset=queryset)
        except AttributeError:
            raise Http404


class DeleteServiceEvent(DeleteView, FormView, PermissionRequiredMixin):

    permission_required = 'service_log.delete_serviceevent'
    raise_exception = True
    model = models.ServiceEvent
    template_name = 'service_log/service_event_delete.html'
    form_class = forms.ServiceEventDeleteForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.form_class(pk=self.object.id)
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):

        self.object = self.get_object()

        models.ServiceLog.objects.log_service_event_delete(
            self.request.user,
            self.object,
            {'reason': form.cleaned_data['reason'], 'comment': form.cleaned_data['comment']}
        )

        success_url = self.get_success_url()
        self.object.set_inactive()

        messages.add_message(self.request, messages.INFO, 'Service event {} deleted'.format(self.object.id))

        return HttpResponseRedirect(success_url)

    def form_invalid(self, form):
        messages.add_message(
            self.request, messages.WARNING, 'Could not delete service event {}'.format(form.instance.id)
        )
        return reverse('sl_dash')

    def get_success_url(self):
        return reverse('sl_dash')


class ServiceEventsBaseList(BaseListableView):
    """
    This view provides a base for any sort of listing of
    :model:`service_log.ServiceEvent`'s.
    """

    model = models.ServiceEvent
    template_name = 'service_log/service_event_list.html'
    paginate_by = 50

    order_by = ['-datetime_service']
    kwarg_filters = None

    fields = (
        'actions',
        'pk',
        'datetime_service',
        'unit_service_area__unit__name',
        'unit_service_area__service_area__name',
        'service_type__name',
        # 'problem_type__name',
        'problem_description',
        'work_description',
        'service_status__name'
    )

    headers = {
        'pk': _('ID'),
        'datetime_service': _('Service Date'),
        'unit_service_area__unit__name': _('Unit'),
        'unit_service_area__service_area__name': _('Service Area'),
        'service_type__name': _('Service Type'),
        # 'problem_type__name': _('Problem Type'),
        'service_status__name': _('Service Status'),
    }

    widgets = {
        'datetime_service': DATE_RANGE,
        'unit_service_area__unit__name': SELECT_MULTI,
        'unit_service_area__service_area__name': SELECT_MULTI,
        'service_type__name': SELECT_MULTI,
        # 'problem_type__name': SELECT_MULTI,
        'service_status__name': SELECT_MULTI
    }

    date_ranges = {
        'datetime_service': [
            YESTERDAY, LAST_WEEK, LAST_7_DAYS, LAST_MONTH, LAST_30_DAYS, LAST_YEAR, LAST_365_DAYS, YEAR_TO_DATE
        ]
    }

    search_fields = {
        'actions': False,
    }

    order_fields = {
        'actions': False,
    }

    select_related = (
        'unit_service_area__unit',
        'unit_service_area__service_area',
        'service_type',
        'service_status'
    )

    def __init__(self, *args, **kwargs):

        super(ServiceEventsBaseList, self).__init__(*args, **kwargs)
        self.templates = {
            'actions': get_template('service_log/table_context_se_actions.html'),
            'datetime_service': get_template('service_log/table_context_datetime.html'),
            'service_status__name': get_template('service_log/service_event_status_label.html'),
            'problem_description': get_template('service_log/table_context_problem_description.html'),
            'work_description': get_template('service_log/table_context_work_description.html'),
        }

    def get_icon(self):
        return 'fa-wrench'

    def get_page_title(self, f=None):
        return 'All Service Events'

    def get_context_data(self, *args, **kwargs):
        context = super(ServiceEventsBaseList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        context['page_title'] = self.get_page_title()
        return context

    def actions(self, se):
        template = self.templates['actions']
        perms = PermWrapper(self.request.user)
        c = {'se': se, 'request': self.request, 'next': self.get_next(), 'perms': perms}
        return template.render(c)

    def get_next(self):
        return reverse('sl_list_all')

    def datetime_service(self, se):
        template = self.templates['datetime_service']
        c = {'datetime': se.datetime_service}
        return template.render(c)

    def service_status__name(self, se):
        template = self.templates['service_status__name']
        c = {'colour': se.service_status.colour, 'name': se.service_status.name, 'request': self.request}
        return template.render(c)

    def problem_description(self, se):
        template = self.templates['problem_description']
        c = {'problem_description': se.problem_description, 'request': self.request}
        return template.render(c)

    def work_description(self, se):
        template = self.templates['work_description']
        c = {'work_description': se.work_description, 'request': self.request}
        return template.render(c)


class ServiceEventsByStatusList(ServiceEventsBaseList):
    """View to show Service Events with a given ServiceEventStatus"""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(service_status_id=self.kwargs['pk'])

    def get_page_title(self, *args, **kwargs):
        status = get_object_or_404(models.ServiceEventStatus, pk=self.kwargs['pk'])
        return "Service Events - Status: %s" % (status.name)

    def get_next(self):
        return reverse('sl_list_by_status', kwargs={'pk': self.kwargs['pk']})


class ServiceEventsReviewRequiredList(ServiceEventsBaseList):
    """View to show Service Events with is_review_required or
    service_status__is_review_required set to True"""

    def get_page_title(self, *args):
        return "Service Events Requiring Review"

    def get_queryset(self):
        qs = super().get_queryset().filter(is_review_required=True,  service_status__is_review_required=True)
        return qs

    def get_next(self):
        return reverse('sl_list_review_required')


class ServiceEventsInitiatedByList(ServiceEventsBaseList):
    """View to show Service Events initiated by a TestListInstance."""

    def get_page_title(self, *args):
        tli = get_object_or_404(qa_models.TestListInstance, pk=self.kwargs['tli_pk'])
        title = "%s %s - %s " % (
            tli.unit_test_collection.unit, tli.unit_test_collection.name,
            timezone.localtime(tli.work_completed).strftime('%b %m, %I:%M %p')
        )
        return "Service Events Initiated By %s" % (title)

    def get_queryset(self):
        tli = get_object_or_404(qa_models.TestListInstance, pk=self.kwargs['tli_pk'])
        return tli.serviceevents_initiated.all()

    def get_next(self):
        return reverse('sl_list_initiated_by', kwargs={'tli_pk': self.kwargs['tli_pk']})


class ServiceEventsReturnToServiceForList(ServiceEventsBaseList):
    """View to show Service Events where a TestListInstance was performed as
    return to service qa."""

    def get_page_title(self, *args):
        tli = get_object_or_404(qa_models.TestListInstance, pk=self.kwargs['tli_pk'])
        title = "%s %s - %s " % (
            tli.unit_test_collection.unit, tli.unit_test_collection.name,
            timezone.localtime(tli.work_completed).strftime('%b %m, %I:%M %p')
        )
        return "Service Events with %s as Return To Service" % (title)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(returntoserviceqa__test_list_instance__id=self.kwargs['tli_pk'])

    def get_next(self):
        return reverse('sl_list_return_to_service_for', kwargs={'tli_pk': self.kwargs['tli_pk']})


class ServiceEventsByUnitList(ServiceEventsBaseList):
    """View to show Service Events for a given unit."""

    def get_page_title(self, *args):
        unit = get_object_or_404(u_models.Unit, number=self.kwargs['unit_number'])
        return "Service Events For %s" % (unit)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(unit_service_area__unit__number=self.kwargs['unit_number'])

    def get_next(self):
        return reverse('sl_list_by_unit', kwargs={'unit__number': self.kwargs['unit_number']})


class ReturnToServiceQABaseList(BaseListableView):

    model = models.ReturnToServiceQA
    template_name = 'service_log/rtsqa_list.html'
    paginate_by = 50

    order_by = ['-service_event__datetime_service']
    kwarg_filters = None

    fields = (
        'actions',
        'service_event__datetime_service',
        'service_event__unit_service_area__unit__name',
        'unit_test_collection__name',
        'test_list_instance__work_completed',
        'test_list_instance_pass_fail',
        'test_list_instance_review_status',
        'service_event__service_status__name'
    )

    headers = {
        'service_event__datetime_service': _('Service Date'),
        'service_event__unit_service_area__unit__name': _('Unit'),
        'unit_test_collection__name': _('Test List'),
        'test_list_instance__work_completed': _('Test List Completed'),
        'test_list_instance_pass_fail': _('Pass/Fail'),
        'test_list_instance_review_status': _('Review Status'),
        'service_event__service_status__name': _('Service Event Status')
    }

    widgets = {
        'service_event__datetime_service': DATE_RANGE,
        'service_event__unit_service_area__unit__name': SELECT_MULTI,
        'service_event__service_status__name': SELECT_MULTI,
        'test_list_instance__work_completed': DATE_RANGE
    }

    date_ranges = {
        'service_event__datetime_service': [TODAY, YESTERDAY, LAST_WEEK, THIS_WEEK, LAST_MONTH, THIS_MONTH, THIS_YEAR],
        'test_list_instance__work_completed': [TODAY, YESTERDAY, LAST_WEEK, THIS_WEEK, LAST_MONTH, THIS_MONTH, THIS_YEAR]
    }

    search_fields = {
        'actions': False,
        'test_list_instance_pass_fail': False,
        'test_list_instance_review_status': False,
        'service_event': 'service_event__id__icontains'
    }

    order_fields = {
        'actions': False,
        'test_list_instance_pass_fail': False,
        'test_list_instance_review_status': False
    }

    select_related = (
        'service_event__unit_service_area__unit',
        'service_event__service_status',
        'test_list_instance__reviewed_by',
        'test_list_instance'
    )

    prefetch_related = (
        'test_list_instance__testinstance_set',
        'test_list_instance__testinstance_set__status',
        'unit_test_collection',
        'test_list_instance__comments'
    )

    def __init__(self, *args, **kwargs):

        super(ReturnToServiceQABaseList, self).__init__(*args, **kwargs)
        self.templates = {
            'actions': get_template("service_log/table_context_rtsqa_actions.html"),
            'service_event__datetime_service': get_template("service_log/table_context_datetime.html"),
            'test_list_instance__work_completed': get_template("service_log/table_context_tli_work_completed.html"),
            'test_list_instance_pass_fail': get_template("qa/pass_fail_status.html"),
            'test_list_instance_review_status': get_template("qa/review_status.html"),
            'service_event__service_status__name': get_template("service_log/service_event_status_label.html"),
        }

    def get_icon(self):
        return 'fa-pencil-square-o'

    def get_page_title(self, f=None):
        return 'All Return To Service QC'

    def get_context_data(self, *args, **kwargs):
        context = super(ReturnToServiceQABaseList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        context['page_title'] = self.get_page_title()
        return context

    def actions(self, rtsqa):
        template = self.templates['actions']
        perms = PermWrapper(self.request.user)
        c = {'rtsqa': rtsqa, 'request': self.request, 'next': self.get_next(), 'show_se_link': True, 'perms': perms}
        return template.render(c)

    def get_next(self):
        return reverse('rtsqa_list_all')

    def test_list_instance_pass_fail(self, rtsqa):
        template = self.templates['test_list_instance_pass_fail']
        c = {
            'instance': rtsqa.test_list_instance if rtsqa.test_list_instance else None,
            'show_dash': True,
            'exclude': ['no_tol'],
            'show_icons': True
        }
        return template.render(c)

    def test_list_instance_review_status(self, rtsqa):
        template = self.templates['test_list_instance_review_status']
        c = {
            'instance': rtsqa.test_list_instance if rtsqa.test_list_instance else None,
            'perms': PermWrapper(self.request.user),
            'request': self.request,
            'show_labels': False,
            'show_dash': True,
            'show_icons': True,
        }
        c.update(generate_review_status_context(rtsqa.test_list_instance))
        return template.render(c)

    def service_event__datetime_service(self, rtsqa):
        template = self.templates['service_event__datetime_service']
        c = {'datetime': rtsqa.service_event.datetime_service}
        return template.render(c)

    def test_list_instance__work_completed(self, rtsqa):
        template = self.templates['test_list_instance__work_completed']
        if rtsqa.test_list_instance:
            c = {
                'datetime_completed': rtsqa.test_list_instance.work_completed,
                'datetime_started': rtsqa.test_list_instance.work_started,
                'in_progress': rtsqa.test_list_instance.in_progress
            }
            return template.render(c)
        return '----'

    def service_event__service_status__name(self, rtsqa):
        template = self.templates['service_event__service_status__name']
        c = {'colour': rtsqa.service_event.service_status.colour, 'name': rtsqa.service_event.service_status.name, 'request': self.request}
        return template.render(c)


class ReturnToServiceQAIncompleteList(ReturnToServiceQABaseList):

    def get_page_title(self):
        return "Return to Service QC - Incomplete"

    def get_queryset(self):
        return super().get_queryset().filter(test_list_instance=None)

    def get_next(self):
        return reverse("rtsqa_list_incomplete")


class ReturnToServiceQAUnreviewedList(ReturnToServiceQABaseList):

    def get_page_title(self):
        return "Return to Service QC - Unreviewed"

    def get_queryset(self):
        return super().get_queryset().filter(
            test_list_instance__isnull=False,
            test_list_instance__all_reviewed=False,
        )

    def get_next(self):
        return reverse("rtsqa_list_unreviewed")


class ReturnToServiceQAForEventList(ReturnToServiceQABaseList):

    def get_page_title(self):
        se = get_object_or_404(models.ServiceEvent, pk=self.kwargs['se_pk'])
        description = "%s - %s %s" % (
            se.unit_service_area,
            timezone.localtime(se.datetime_service).strftime('%b %m, %I:%M %p'),
            qa_tags.service_status_label(se.service_status),
        )
        return mark_safe("Return to Service QC - Service Event %d: %s" % (se.pk, description))

    def get_queryset(self):
        get_object_or_404(models.ServiceEvent, pk=self.kwargs['se_pk'])
        return super().get_queryset().filter(service_event_id=self.kwargs['se_pk'])

    def get_next(self):
        return reverse("rtsqa_list_for_event", kwargs={'se_pk': self.kwargs['se_pk']})


class TLISelect(UTCInstances):

    rtsqa = None

    def get_page_title(self):
        try:
            utc = models.UnitTestCollection.objects.get(pk=self.kwargs["pk"])
            return "Select a %s instance" % utc.name
        except:
            raise Http404

    def actions(self, tli):
        template = self.templates['actions']
        c = {"instance": tli, "perms": PermWrapper(self.request.user), "select": True, 'f_form': self.kwargs['form']}
        return template.render(c)


@login_required
def tli_statuses(request):

    try:
        tli = qa_models.TestListInstance.objects.get(pk=request.GET.get('tli_id'))
    except ObjectDoesNotExist:
        raise Http404

    return JsonResponse(
        {
            'pass_fail': tli.pass_fail_summary(),
            'review': tli.review_summary(),
            'datetime': timezone.localtime(tli.created).replace(microsecond=0),
            'all_reviewed': int(tli.all_reviewed),
            'work_completed': timezone.localtime(tli.work_completed).replace(microsecond=0),
            'in_progress': tli.in_progress
        },
        safe=False
    )


class ChooseUnitForNewSE(ChooseUnit):
    template_name = 'units/unittype_choose_for_service_event.html'
    split_sites = True
    unit_serviceable_only = True

    def get_context_data(self, *args, **kwargs):
        context = super(ChooseUnitForNewSE, self).get_context_data(*args, **kwargs)
        context['new_se'] = True
        return context


class ChooseUnitForViewSE(ChooseUnit):
    template_name = 'units/unittype_choose_for_service_event.html'
    split_sites = True


class ServiceEventDownTimesList(ServiceEventsBaseList):

    template_name = 'service_log/service_event_down_time.html'
    model = models.ServiceEvent

    fields = (
        'actions',
        # 'pk',
        'datetime_service',
        'unit_service_area__unit__name',
        'unit_service_area__unit__type__name',
        'unit_service_area__unit__active',
        'unit_service_area__service_area__name',
        # 'service_type__name',
        'problem_description',
        'duration_service_time',
        'duration_lost_time'
    )

    headers = {
        # 'pk': _('ID'),
        'datetime_service': _('Service Date'),
        'unit_service_area__unit__name': _('Unit'),
        'unit_service_area__unit__type__name': _('Unit Type'),
        'unit_service_area__unit__active': _('Active'),
        'unit_service_area__service_area__name': _('Service Area'),
        # 'service_type__name': _('Service Type'),
        'duration_service_time': _('Service Time (hh:mm)'),
        'duration_lost_time': _('Lost Time (hh:mm)')
    }

    widgets = {
        'datetime_service': DATE_RANGE,
        'unit_service_area__unit__name': SELECT_MULTI,
        'unit_service_area__unit__type__name': SELECT_MULTI,
        'unit_service_area__unit__active': SELECT,
        'unit_service_area__service_area__name': SELECT_MULTI,
        # 'service_type__name': SELECT_MULTI
    }

    date_ranges = {
        'datetime_service': [
            YESTERDAY, LAST_WEEK, LAST_7_DAYS, LAST_MONTH, LAST_30_DAYS, LAST_YEAR, LAST_365_DAYS, YEAR_TO_DATE
        ]
    }

    search_fields = {
        'actions': False,
        'duration_service_time': False,
        'duration_lost_time': False
    }

    order_fields = {
        'actions': False,
        'unit_service_area__unit__active': False
    }

    select_related = (
        'unit_service_area__unit',
        'unit_service_area__unit__type',
        'unit_service_area__service_area',
        # 'service_type',
        'service_status'
    )

    def get_page_title(self, f=None):
        return 'Filter Service Events and Up Time Summary'

    def duration_lost_time(self, se):
        duration = se.duration_lost_time
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            return '{}:{:02}'.format(hours, minutes)

    def duration_service_time(self, se):
        duration = se.duration_service_time
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            return '{}:{:02}'.format(hours, minutes)


@login_required
def handle_unit_down_time(request):

    se_qs = models.ServiceEvent.objects.select_related(
        'service_type', 'unit_service_area__service_area', 'unit_service_area__unit'
    ).all()

    daterange = request.GET.get('daterange', False)

    if daterange:
        tz = timezone.get_current_timezone()
        date_from = timezone.datetime.strptime(daterange.split(' - ')[0], '%d %b %Y')
        date_to = timezone.datetime.strptime(daterange.split(' - ')[1], '%d %b %Y')
        date_to = timezone.datetime(year=date_to.year, month=date_to.month, day=date_to.day, hour=23, minute=59, second=59)
        date_from = tz.localize(date_from)
        date_to = tz.localize(date_to)
        se_qs = se_qs.filter(datetime_service__gte=date_from, datetime_service__lte=date_to)
        date_to = date_to.date()
        date_from = date_from.date()
    else:
        date_from = None
        date_to = timezone.datetime.now().date()
        date_to = timezone.datetime(year=date_to.year, month=date_to.month, day=date_to.day, hour=23, minute=59, second=59, tzinfo=timezone.get_current_timezone())
        se_qs = se_qs.filter(datetime_service__lte=date_to)
        date_to = date_to.date()

    service_areas = request.GET.getlist('service_area', False)
    if service_areas:
        se_qs = se_qs.filter(unit_service_area__service_area__name__in=service_areas)

    problem_description = request.GET.get('problem_description', False)
    if problem_description:
        se_qs = se_qs.filter(problem_description__icontains=problem_description)

    units = request.GET.getlist('unit', False)
    if units:
        se_qs = se_qs.filter(unit_service_area__unit__name__in=units)
        units = u_models.Unit.objects.filter(name__in=units).prefetch_related(
            'unitavailabletime_set', 'unitavailabletimeedit_set'
        ).select_related('type')
    else:
        units = u_models.Unit.objects.all().prefetch_related(
            'unitavailabletime_set', 'unitavailabletimeedit_set'
        ).select_related('type')

    units = units.filter(id__in=se_qs.values_list('unit_service_area__unit', flat=True).distinct())

    unit_types = request.GET.getlist('unit__type', False)
    if unit_types:
        se_qs = se_qs.filter(unit_service_area__unit__type__name__in=unit_types)
        units = units.filter(type__name__in=unit_types)

    unit_active = request.GET.get('unit__active', None)
    if unit_active is not None:
        unit_active = unit_active == 'True'
        se_qs = se_qs.filter(unit_service_area__unit__active=unit_active)
        units = units.filter(active=unit_active)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="qatrack_unit_uptime.csv"'
    response['Content-Type'] = 'text/csv; charset=utf-8'

    totals = OrderedDict({'potential': 0})

    writer = csv.writer(response)
    rows = [
        ['Up Time Report: ' + (date_from.strftime('%d %b %Y') + ' to ' + date_to.strftime('%d %b %Y')) if daterange else 'Up Time Report: All time until ' + timezone.datetime.now().strftime('%d %b %Y')],
        [''],
        [''],
        [''],
        ['Unit Name', 'Unit Type', 'Available Time Hrs'],
    ]

    all_service_types = models.ServiceType.objects.all()
    for t in all_service_types:
        rows[4].append('# ' + t.name + ' Repairs')
        rows[4].append(t.name + ' Service Hrs')
        rows[4].append(t.name + ' Lost Hrs')
        totals[t.name + '-repairs'] = 0
        totals[t.name + '-service'] = 0
        totals[t.name + '-lost'] = 0
    rows[4] += ['Total Service Hrs', 'Total Lost Hrs', 'Total #']

    totals['total_service'] = 0
    totals['total_lost'] = 0
    totals['total_num'] = 0

    if not service_areas:
        rows[4].append('% Up Time')
        totals['available'] = 0
    else:
        rows[1] = ['For Service Areas: ', ''] + [sa for sa in service_areas]

    if problem_description:
        rows[2] = ['Service Events with Problem Description containing: ', '', '', '', '', '', problem_description]

    for u in units:

        service_events_unit_qs = se_qs.filter(unit_service_area__unit=u)
        potential_time = u.get_potential_time(date_from, date_to)
        unit_vals = [
            u.name,
            u.type.name,
            '{:.2f}'.format(potential_time) if potential_time > 0 else '0'
        ]
        totals['potential'] += potential_time

        for t in all_service_types:
            seu_type_q = service_events_unit_qs.filter(service_type=t)
            repairs = len(seu_type_q)
            service = seu_type_q.aggregate(Sum('duration_service_time'))['duration_service_time__sum']
            lost = seu_type_q.aggregate(Sum('duration_lost_time'))['duration_lost_time__sum']

            service = service.total_seconds() / 3600 if service else 0
            lost = lost.total_seconds() / 3600 if lost else 0

            unit_vals.append(repairs)
            unit_vals.append('{:.2f}'.format(service))
            unit_vals.append('{:.2f}'.format(lost))

            totals[t.name + '-repairs'] += repairs
            totals[t.name + '-service'] += service
            totals[t.name + '-lost'] += lost

        total_lost_time = service_events_unit_qs.aggregate(Sum('duration_lost_time'))['duration_lost_time__sum']
        total_lost_time = total_lost_time.total_seconds() / 3600 if total_lost_time else 0

        total_service_time = service_events_unit_qs.aggregate(Sum('duration_service_time'))['duration_service_time__sum']
        total_service_time = total_service_time.total_seconds() / 3600 if total_service_time else 0

        total_num = len(service_events_unit_qs)

        unit_vals += ['{:.2f}'.format(total_service_time), '{:.2f}'.format(total_lost_time), total_num]

        if not service_areas:
            available = ((potential_time - total_lost_time) / potential_time) * 100 if potential_time > 0 else 0
            totals['available'] += available
            unit_vals.append('{:.2f}'.format(available))

        totals['total_service'] += total_service_time
        totals['total_lost'] += total_lost_time
        totals['total_num'] += total_num

        rows.append(unit_vals)

    for t in all_service_types:
        totals[t.name + '-service'] = '{:.2f}'.format(totals[t.name + '-service'])
        totals[t.name + '-lost'] = '{:.2f}'.format(totals[t.name + '-lost'])
    totals['total_service'] = '{:.2f}'.format(totals['total_service'])
    totals['total_lost'] = '{:.2f}'.format(totals['total_lost'])

    if not service_areas:
        totals['available'] = '{:.2f}'.format(totals['available'] / len(units)) if len(units) is not 0 else 0
    rows += [[''], ['']]
    rows.append(['', 'Totals:'] + [str(totals[t]) for t in totals])

    for r in rows:
        writer.writerow(r)

    return response
