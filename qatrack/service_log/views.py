from collections import OrderedDict

from braces.views import LoginRequiredMixin, PermissionRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse, resolve
from django.forms.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, DetailView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView

from listable.views import (
    BaseListableView, DATE_RANGE, SELECT_MULTI,
    TODAY, YESTERDAY, LAST_WEEK, THIS_WEEK, LAST_MONTH, THIS_MONTH, THIS_YEAR
)

if settings.USE_PARTS:
    from qatrack.parts import forms as p_forms
    from qatrack.parts import models as p_models
from qatrack.service_log import models, forms
from qatrack.qa import models as qa_models
from qatrack.qa.views.base import generate_review_status_context
from qatrack.qa.views.review import UTCInstances
from qatrack.qa.views.perform import ChooseUnit
from qatrack.units import models as u_models


def get_time_display(dt):

    if not isinstance(dt, timezone.datetime):
        raise ValueError('%s is not a valid datetime' % dt)
    if timezone.now() - dt < timezone.timedelta(hours=1):
        ago = timezone.now() - dt
        # ago = timezone.timedelta(minutes=ago.minute)
        return str(ago.seconds // 60) + ' minutes ago'
    else:
        return dt.strftime('%I:%M %p')


def populate_timeline_from_queryset(unsorted_dict, obj, datetime, obj_class, msg=''):

    date = datetime.date()
    time = get_time_display(datetime)

    if obj_class == 'rtsqa_complete':
        statuses_dict = generate_review_status_context(obj.test_list_instance)
    else:
        statuses_dict = {}

    if date not in unsorted_dict:

        if date == timezone.now().date():
            display = _('Today')
        elif date == (timezone.now() - timezone.timedelta(days=1)).date():
            display = _('Yesterday')
        else:
            display = date

        unsorted_dict.update({date: {
            'objs': [{
                'class': obj_class,
                'instance': obj,
                'time': time,
                'datetime': datetime,
                'msg': msg,
                'statuses_dict': statuses_dict
            }],
            'display': display,
        }})
    else:
        unsorted_dict[date]['objs'].append({
            'class': obj_class,
            'instance': obj,
            'time': time,
            'datetime': datetime,
            'msg': msg,
            'statuses_dict': statuses_dict
        })

    return unsorted_dict


def unit_sa_utc(request):

    unit = models.Unit.objects.get(id=request.GET['unit_id'])
    service_areas = list(models.ServiceArea.objects.filter(units=unit).values())

    # testlist_ct = ContentType.objects.get(app_label="qa", model="testlist")
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
    se_search = request.GET['q']
    unit_id = request.GET['unit_id']
    service_events = models.ServiceEvent.objects \
        .filter(id__icontains=se_search, unit_service_area__unit=unit_id) \
        .order_by('-id') \
        .select_related('service_status')[0:50]\
        .values_list('id', 'service_status__id', 'problem_description')
    return JsonResponse({'colour_ids': list(service_events)})


def get_user_name(user):
    return user.username if not user.first_name or not user.last_name else user.first_name + ' ' + user.last_name


class SLDashboard(TemplateView):

    template_name = "service_log/sl_dash.html"

    def get_counts(self):

        # TODO: Parts low
        rtsqa_qs = models.ReturnToServiceQA.objects.prefetch_related().all()
        default_status = models.ServiceEventStatus.objects.get(is_default=True)
        to_return = {
            'qa_not_reviewed': rtsqa_qs.filter(test_list_instance__isnull=False, test_list_instance__all_reviewed=False).count(),
            'qa_not_complete': rtsqa_qs.filter(test_list_instance__isnull=True).count(),
            'units_restricted': models.Unit.objects.filter(restricted=True).count(),
            'parts_low': 0,
            'se_statuses': {},
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
        # qs = models.ServiceEventStatus.objects.filter(is_active=True).order_by('pk')
        # for s in qs:
        #     to_return['se_statuses'][s.name] = {
        #         'num': models.ServiceEvent.objects.filter(service_status=s).count(),
        #         'id': s.id
        #     }
        return to_return

    def get_timeline(self):

        se_new = models.ServiceEvent.objects.filter(
            datetime_created__gt=timezone.now() - timezone.timedelta(days=14)
        ).select_related('unit_service_area__unit', 'user_created_by').order_by('-datetime_created')[:40]

        se_edited = models.ServiceEvent.objects.filter(
            datetime_modified__gt=timezone.now() - timezone.timedelta(days=14)
        ).select_related('unit_service_area__unit', 'user_modified_by').order_by('-datetime_modified')[:40]

        se_status = models.ServiceEvent.objects.filter(
            datetime_status_changed__gt=timezone.now() - timezone.timedelta(days=14)
        ).select_related(
            'service_status', 'unit_service_area__unit', 'user_status_changed_by'
        ).order_by('-datetime_status_changed')[:40]

        rtsqa_new = models.ReturnToServiceQA.objects.filter(
            datetime_assigned__gt=timezone.now() - timezone.timedelta(days=14)
        ).select_related(
            'service_event',
            'test_list_instance',
            'unit_test_collection',
            'service_event__unit_service_area__unit',
            'user_assigned_by'
        ).prefetch_related(
            'test_list_instance__comments',
            'test_list_instance__testinstance_set',
            'test_list_instance__testinstance_set__status',
            'unit_test_collection__tests_object'
        ).order_by('-datetime_assigned')[:40]

        rtsqa_complete = models.ReturnToServiceQA.objects.filter(
            test_list_instance__isnull=False,
            test_list_instance__work_completed__gt=timezone.now() - timezone.timedelta(days=14)
        ).select_related(
            'service_event',
            'test_list_instance',
            'unit_test_collection',
            'service_event__unit_service_area__unit',
            'test_list_instance__created_by',
            'test_list_instance__reviewed_by',
        ).prefetch_related(
            'test_list_instance__comments',
            'test_list_instance__testinstance_set',
            'test_list_instance__testinstance_set__status',
            'unit_test_collection__tests_object'
        ).order_by('-test_list_instance__created')[:40]

        unsorted_dict = {}

        for se in se_edited:
            datetime = timezone.localtime(se.datetime_modified)
            msg = get_user_name(se.user_modified_by) + ' modified service event ' + str(se.id)
            populate_timeline_from_queryset(unsorted_dict, se, datetime, 'se_edit', msg=msg)

        for se in se_status:
            datetime = timezone.localtime(se.datetime_status_changed)
            msg = get_user_name(se.user_status_changed_by) + ' changed status of service event ' + str(se.id) + ' to '
            populate_timeline_from_queryset(unsorted_dict, se, datetime, 'se_status', msg=msg)

        for se in se_new:
            datetime = timezone.localtime(se.datetime_created)
            msg = get_user_name(se.user_created_by) + ' created service event ' + str(se.id)
            populate_timeline_from_queryset(unsorted_dict, se, datetime, 'se_new', msg=msg)

        for rtsqa in rtsqa_new:
            datetime = timezone.localtime(rtsqa.datetime_assigned)
            msg = (
                get_user_name(rtsqa.user_assigned_by) +
                ' assigned a new RTS QA (' +
                rtsqa.unit_test_collection.tests_object.name +
                ') for service event ' +
                str(rtsqa.service_event.id)
            )
            populate_timeline_from_queryset(unsorted_dict, rtsqa, datetime, 'rtsqa_new', msg=msg)

        for rtsqa in rtsqa_complete:
            datetime = timezone.localtime(rtsqa.test_list_instance.created)
            msg = (
                get_user_name(rtsqa.test_list_instance.created_by) +
                ' performed a RTS QA (' +
                rtsqa.unit_test_collection.tests_object.name +
                ') for service event ' +
                str(rtsqa.service_event.id)
            )
            populate_timeline_from_queryset(unsorted_dict, rtsqa, datetime, 'rtsqa_complete', msg=msg)

        for ud in unsorted_dict:
            unsorted_dict[ud]['objs'] = sorted(unsorted_dict[ud]['objs'], key=lambda obj: obj['datetime'], reverse=True)
        ordered_dict = OrderedDict(sorted(unsorted_dict.items(), reverse=True))

        return ordered_dict

    def get_context_data(self, **kwargs):

        context = super(SLDashboard, self).get_context_data()
        context['counts'] = self.get_counts()
        context['tl_dates'] = self.get_timeline()

        return context

    def dispatch(self, request, *args, **kwargs):
        if models.ServiceEventStatus.objects.all().exists():
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

    # def get_object(self, queryset=None):
    #     try:
    #         return super(ServiceEventUpdateCreate, self).get_object(queryset)
    #     except AttributeError:
    #         return None

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

        if self.request.method == 'POST':

            context_data['hours_formset'] = forms.HoursFormset(
                self.request.POST,
                instance=self.object,
                prefix='hours'
            )
            context_data['rtsqa_formset'] = forms.ReturnToServiceQAFormset(
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
            context_data['rtsqa_formset'] = forms.ReturnToServiceQAFormset(
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

        return context_data

    def form_valid(self, form):

        context = self.get_context_data()
        hours_formset = context["hours_formset"]
        rtsqa_formset = context["rtsqa_formset"]

        if settings.USE_PARTS:
            parts_formset = context['part_used_formset']
            if not parts_formset or not parts_formset.is_valid():
                return self.render_to_response(context)

        if not hours_formset.is_valid() or not rtsqa_formset.is_valid():
            return self.render_to_response(context)

        service_event = form.save()
        service_event_related = form.cleaned_data.get('service_event_related_field')
        try:
            sers = models.ServiceEvent.objects.filter(pk__in=service_event_related)
        except ValueError:
            sers = []
        service_event.service_event_related = sers

        if 'service_status' in form.changed_data:
            se_needing_review_count = models.ServiceEvent.objects.filter(
                service_status__in=models.ServiceEventStatus.objects.filter(is_review_required=True),
                is_review_required=True
            ).count()
            cache.set('se_needing_review_count', se_needing_review_count)

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

                obj_type, obj_id = user_or_thirdparty.split('-')
                user = None
                third_party = None
                if obj_type == 'user':
                    user = User.objects.get(id=obj_id)
                elif obj_type == 'tp':
                    third_party = models.ThirdParty.objects.get(id=obj_id)

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

                initial_p = None if is_new else p_form.initial['part']
                if delete:
                    current_p = p_form.initial['part']
                else:
                    current_p = p_form.cleaned_data['part']

                initial_s = p_form.initial['from_storage'] if 'from_storage' in p_form.initial else None
                current_s = p_form.cleaned_data['from_storage'] if 'from_storage' in p_form.cleaned_data else None

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
                current_qty = p_form.cleaned_data['quantity'] if 'quantity' in p_form.cleaned_data else initial_qty
                change = current_qty - initial_qty

                if delete and not is_new:
                    if current_psc:
                        qty = pu_instance.quantity
                        current_psc.quantity += qty

                        if current_psc:
                            # if current_psc.quantity <= 0:
                            #     if current_psc.id:
                            #         current_psc.delete()
                            # else:
                            current_psc.save()

                        if initial_psc:
                            # if initial_psc.quantity <= 0:
                            #     if initial_psc.id:
                            #         initial_psc.delete()
                            # else:
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

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        return reverse("sl_dash")


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

        return super(CreateServiceEvent, self).form_valid(form)


class UpdateServiceEvent(ServiceEventUpdateCreate):

    def form_valid(self, form):

        self.instance = form.save(commit=False)

        if 'is_review_required_fake' in form.changed_data:
            form.changed_data.remove('is_review_required_fake')

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

            # If service status was not changed explicitly, but needs to be reset to default status due to other changes.
            if not form.instance.service_status.is_review_required:
                form.instance.service_status = models.ServiceEventStatus.get_default()

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

        return context_data


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
        'datetime_service': [TODAY, YESTERDAY, LAST_WEEK, THIS_WEEK, LAST_MONTH, THIS_MONTH, THIS_YEAR]
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
        }

    def get_icon(self):
        return 'fa-wrench'

    def get_page_title(self, f=None):
        if not f:
            return 'All Service Events'
        to_return = 'Service Events'
        filters = f.split('_')
        for filt in filters:
            [key, val] = filt.split('-')
            if key == 'ss':
                to_return = to_return + ' - Status: ' + models.ServiceEventStatus.objects.get(pk=val).name
            elif key == 'ar':
                to_return = to_return + ' - Review is ' + ((not bool(int(val))) * 'not ') + 'required'
            elif key == 'u':
                to_return = to_return + ' - ' + u_models.Unit.objects.get(pk=val).name
            elif key == 'id':
                to_return = ' with IDs ' + val

        return to_return

    def get(self, request, *args, **kwargs):
        if self.kwarg_filters is None:
            self.kwarg_filters = kwargs.pop('f', None)
        return super(ServiceEventsBaseList, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(ServiceEventsBaseList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        f = self.request.GET.get('f', False)
        context['kwargs'] = {'f': f} if f else {}
        context['page_title'] = self.get_page_title(f)
        return context

    def get_queryset(self):
        qs = super(ServiceEventsBaseList, self).get_queryset()

        if self.kwarg_filters is None:
            self.kwarg_filters = self.request.GET.get('f', None)

        if self.kwarg_filters is not None:
            filters = self.kwarg_filters.split('_')
            for filt in filters:
                [key, val] = filt.split('-')
                if key == 'ss':
                    qs = qs.filter(service_status=val)
                elif key == 'ar':
                    qs = qs.filter(is_review_required=bool(int(val)))
                elif key == 'ss.ar':
                    qs = qs.filter(service_status__is_review_required=bool(int(val)))
                elif key == 'u':
                    qs = qs.filter(unit_service_area__unit_id=val)
                elif key == 'id':
                    qs = qs.filter(pk__in=val.split(','))

        return qs

    def format_col(self, field, obj):
        col = super(ServiceEventsBaseList, self).format_col(field, obj)
        return col

    def actions(self, se):
        template = self.templates['actions']
        mext = reverse('sl_list_all') + (('?f=' + self.kwarg_filters) if self.kwarg_filters else '')
        perms = PermWrapper(self.request.user)
        c = {'se': se, 'request': self.request, 'next': mext, 'perms': perms}
        return template.render(c)

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


class ReturnToServiceQABaseList(BaseListableView):

    model = models.ReturnToServiceQA
    template_name = 'service_log/rtsqa_list.html'
    paginate_by = 50

    order_by = ['-datetime_assigned']
    kwarg_filters = None

    fields = (
        'actions',
        'pk',
        'datetime_assigned',
        'service_event__unit_service_area__unit__name',
        'unit_test_collection__name',
        'test_list_instance_pass_fail',
        'test_list_instance_review_status',
        'service_event__service_status__name'
    )

    headers = {
        'pk': _('ID'),
        'datetime_assigned': _('Date Assigned'),
        'service_event__unit_service_area__unit__name': _('Unit'),
        'unit_test_collection__name': _('Test List'),
        'test_list_instance_pass_fail': _('Pass/Fail'),
        'test_list_instance_review_status': _('Review Status'),
        'service_event__service_status__name': _('Service Event Status')
    }

    widgets = {
        'datetime_assigned': DATE_RANGE,
        'service_event__unit_service_area__unit__name': SELECT_MULTI,
        'service_event__service_status__name': SELECT_MULTI
    }

    date_ranges = {
        'datetime_assigned': [TODAY, YESTERDAY, LAST_WEEK, THIS_WEEK, LAST_MONTH, THIS_MONTH, THIS_YEAR]
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
        'service_event__service_status'
    )

    prefetch_related = (
        "test_list_instance__testinstance_set",
        "test_list_instance__testinstance_set__status",
        'unit_test_collection'
    )

    def __init__(self, *args, **kwargs):

        super(ReturnToServiceQABaseList, self).__init__(*args, **kwargs)
        self.templates = {
            'actions': get_template("service_log/table_context_rtsqa_actions.html"),
            'datetime_assigned': get_template("service_log/table_context_datetime.html"),
            'test_list_instance_pass_fail': get_template("qa/pass_fail_status.html"),
            'test_list_instance_review_status': get_template("qa/review_status.html"),
            'service_event__service_status__name': get_template("service_log/service_event_status_label.html"),
        }

    def get_icon(self):
        return 'fa-pencil-square-o'

    def get_page_title(self, f=None):
        if not f:
            return 'All RTS QA'
        to_return = 'RTS QA'
        filters = f.split('_')
        for filt in filters:
            [key, val] = filt.split('-')
            if key == 'tli.in':
                if bool(int(val)):
                    to_return += ' - Incomplete'
                else:
                    to_return += ' - Complete'
            elif key == 'tli.ar':
                if bool(int(val)):
                    to_return += ' - Reviewed'
                else:
                    to_return += ' - Not Reviewed'
            elif key == 'ses.irr':
                to_return += ' - Service Event Status Not: '
                names = []
                for s in models.ServiceEventStatus.objects.filter(is_review_required=False):
                    names.append(s.name)
                to_return += ','.join(names)

        return to_return

    def get(self, request, *args, **kwargs):
        if self.kwarg_filters is None:
            self.kwarg_filters = kwargs.pop('f', None)
        return super(ReturnToServiceQABaseList, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(ReturnToServiceQABaseList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        f = self.request.GET.get('f', False)
        context['kwargs'] = {'f': f} if f else {}
        context['page_title'] = self.get_page_title(f)
        return context

    def get_queryset(self):
        qs = super(ReturnToServiceQABaseList, self).get_queryset()

        if self.kwarg_filters is None:
            self.kwarg_filters = self.request.GET.get('f', None)

        if self.kwarg_filters is not None:
            filters = self.kwarg_filters.split('_')
            query_kwargs = {}
            for filt in filters:
                [key, val] = filt.split('-')
                if key == 'tli.in':
                    query_kwargs['test_list_instance__isnull'] = bool(int(val))
                elif key == 'tli.ar':
                    query_kwargs['test_list_instance__all_reviewed'] = bool(int(val))
                elif key == 'ses.irr':
                    query_kwargs['service_event__service_status__is_review_required'] = bool(int(val))

            qs = qs.filter(**query_kwargs)

        return qs

    def actions(self, rtsqa):
        template = self.templates['actions']
        next = reverse('rtsqa_list_all') + (('?f=' + self.kwarg_filters) if self.kwarg_filters else '')
        perms = PermWrapper(self.request.user)
        c = {'rtsqa': rtsqa, 'request': self.request, 'next': next, 'show_se_link': True, 'perms': perms}
        return template.render(c)

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
            'show_dash': True,
        }
        c.update(generate_review_status_context(rtsqa.test_list_instance))
        return template.render(c)

    def datetime_assigned(self, rtsqa):
        template = self.templates['datetime_assigned']
        c = {'datetime': rtsqa.datetime_assigned}
        return template.render(c)

    def service_event__service_status__name(self, rtsqa):
        template = self.templates['service_event__service_status__name']
        c = {'colour': rtsqa.service_event.service_status.colour, 'name': rtsqa.service_event.service_status.name, 'request': self.request}
        return template.render(c)


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


def tli_statuses(request):
    tli = qa_models.TestListInstance.objects.get(pk=request.GET.get('tli_id'))
    return JsonResponse(
        {
            'pass_fail': tli.pass_fail_summary(),
            'review': tli.review_summary(),
            'datetime': timezone.localtime(tli.created),
            'all_reviewed': int(tli.all_reviewed)
        },
        safe=False
    )


class ChooseUnitForNewSE(ChooseUnit):
    template_name = 'units/unittype_choose_for_service_event.html'
    split_sites = True

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
        'unit_service_area__service_area__name',
        'service_type__name',
        'problem_description',
        'duration_service_time',
        'duration_lost_time'
    )

    headers = {
        # 'pk': _('ID'),
        'datetime_service': _('Service Date'),
        'unit_service_area__unit__name': _('Unit'),
        'unit_service_area__service_area__name': _('Service Area'),
        'service_type__name': _('Service Type'),
        'duration_service_time': _('Service Time'),
        'duration_lost_time': _('Lost Time')
    }

    widgets = {
        'datetime_service': DATE_RANGE,
        'unit_service_area__unit__name': SELECT_MULTI,
        'unit_service_area__service_area__name': SELECT_MULTI,
        'service_type__name': SELECT_MULTI
    }

    date_ranges = {
        'datetime_service': [TODAY, YESTERDAY, LAST_WEEK, THIS_WEEK, LAST_MONTH, THIS_MONTH, THIS_YEAR]
    }

    search_fields = {
        'actions': False,
        'duration_service_time': False,
        'duration_lost_time': False
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

    def duration_lost_time(self, se):
        duration = se.duration_lost_time
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            return '{}:{}'.format(hours, minutes)

    def duration_service_time(self, se):
        duration = se.duration_service_time
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            return '{}:{:02}'.format(hours, minutes)


class DownTimesSummary(TemplateView):

    template_name = 'service_log/service_event_down_time_summary.html'
