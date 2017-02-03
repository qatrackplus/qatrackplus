
import json

from collections import OrderedDict
from braces.views import LoginRequiredMixin
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse, resolve
from django.db.models import Q
from django.forms.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, DetailView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView

from listable.views import (
    BaseListableView, DATE_RANGE, SELECT_MULTI, NONEORNULL, TEXT,
    TODAY, YESTERDAY, TOMORROW, LAST_WEEK, THIS_WEEK, NEXT_WEEK, LAST_14_DAYS, LAST_MONTH, THIS_MONTH, THIS_YEAR
)

from qatrack.service_log import models, forms
from qatrack.qa import models as qa_models
from qatrack.qa.views.base import generate_review_status_context
from qatrack.qa.views.review import UTCInstances
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

    if obj_class == 'qaf_complete':
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


def get_user_name(user):
    return user.username if not user.first_name or not user.last_name else user.first_name + ' ' + user.last_name


class SLDashboard(TemplateView):

    template_name = "service_log/sl_dash.html"

    def get_counts(self):

        # TODO: Parts low
        qaf_qs = models.QAFollowup.objects.filter()
        default_status = models.ServiceEventStatus.objects.get(is_default=True)
        to_return = {
            'qa_not_reviewed': qaf_qs.filter(test_list_instance__isnull=False, test_list_instance__all_reviewed=False).count(),
            'qa_not_complete': qaf_qs.filter(test_list_instance__isnull=True).count(),
            'units_restricted': models.Unit.objects.filter(restricted=True).count(),
            'parts_low': 0,
            'se_statuses': {},
            'se_needing_approval': models.ServiceEvent.objects.filter(service_status__in=models.ServiceEventStatus.objects.filter(is_approval_required=True), is_approval_required=True).count(),
            'se_default': {'status_name': default_status.name, 'id': default_status.id, 'count': models.ServiceEvent.objects.filter(service_status=default_status).count()}
        }
        # qs = models.ServiceEventStatus.objects.filter(is_active=True).order_by('pk')
        # for s in qs:
        #     to_return['se_statuses'][s.name] = {
        #         'num': models.ServiceEvent.objects.filter(service_status=s).count(),
        #         'id': s.id
        #     }
        return to_return

    def get_timeline(self):

        last_week_date = timezone.now().date() - timezone.timedelta(days=7)
        last_week_datetime = timezone.datetime(year=last_week_date.year, month=last_week_date.month, day=last_week_date.day)
        se_new = models.ServiceEvent.objects\
            .filter(datetime_created__gt=last_week_datetime)\
            .order_by('-datetime_created')
        se_edited = models.ServiceEvent.objects\
            .filter(datetime_modified__gt=last_week_datetime)\
            .order_by('-datetime_modified')
        se_status = models.ServiceEvent.objects\
            .filter(datetime_status_changed__gt=last_week_datetime)\
            .select_related('service_status')\
            .order_by('-datetime_status_changed')
        qaf_new = models.QAFollowup.objects\
            .filter(datetime_assigned__gt=last_week_datetime)\
            .select_related('service_event', 'test_list_instance', 'unit_test_collection')\
            .order_by('-datetime_assigned')
        qaf_complete = models.QAFollowup.objects\
            .filter(test_list_instance__isnull=False, test_list_instance__created__gt=last_week_datetime)\
            .select_related('service_event', 'test_list_instance', 'unit_test_collection')\
            .order_by('-test_list_instance__created')

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

        for qaf in qaf_complete:
            datetime = timezone.localtime(qaf.test_list_instance.created)
            msg = get_user_name(qaf.test_list_instance.created_by) + ' performed a followup (' + qaf.unit_test_collection.tests_object.name + ') for service event ' + str(qaf.service_event.id)
            populate_timeline_from_queryset(unsorted_dict, qaf, datetime, 'qaf_complete', msg=msg)

        for qaf in qaf_new:
            datetime = timezone.localtime(qaf.datetime_assigned)
            msg = get_user_name(qaf.user_assigned_by) + ' assigned a new followup (' + qaf.unit_test_collection.tests_object.name + ') for service event ' + str(qaf.service_event.id)
            populate_timeline_from_queryset(unsorted_dict, qaf, datetime, 'qaf_new', msg=msg)

        for ud in unsorted_dict:
            unsorted_dict[ud]['objs'] = sorted(unsorted_dict[ud]['objs'], key=lambda obj: obj['datetime'], reverse=True)
        ordered_dict = OrderedDict(sorted(unsorted_dict.items(), reverse=True))

        return ordered_dict

    def get_context_data(self, **kwargs):

        context = super(SLDashboard, self).get_context_data()
        context['counts'] = self.get_counts()
        context['tl_dates'] = self.get_timeline()

        return context


class ServiceEventUpdateCreate(LoginRequiredMixin, SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    """
    CreateView and UpdateView functionality combined
    """

    model = models.ServiceEvent
    # form_class = AuthorForm
    template_name = 'service_log/service_event_update.html'
    form_class = forms.ServiceEventForm

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super(ServiceEventUpdateCreate, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        try:
            return super(ServiceEventUpdateCreate, self).get_object(queryset)
        except AttributeError:
            return None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(ServiceEventUpdateCreate, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(ServiceEventUpdateCreate, self).post(request, *args, **kwargs)

    # def get_form(self):
    #     return self.form_class(**self.get_form_kwargs())
    def get_form_kwargs(self):
        kwargs = super(ServiceEventUpdateCreate, self).get_form_kwargs()
        # group_linkers = models.GroupLinker.objects.all()
        kwargs['group_linkers'] = models.GroupLinker.objects.all()
        kwargs['user'] = self.user
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context_data = super(ServiceEventUpdateCreate, self).get_context_data(**kwargs)
        if self.request.method == 'POST':
            context_data['se_statuses'] = {se.id: se.service_status.id for se in models.ServiceEvent.objects.filter(pk__in=self.request.POST.getlist('service_event_related_field'))}
        elif self.object:
            context_data['se_statuses'] = {se.id: se.service_status.id for se in self.object.service_event_related.all()}
        else:
            context_data['se_statuses'] = {}
        context_data['status_tag_colours'] = models.ServiceEventStatus.get_colour_dict()
        context_data['se_types_approval'] = {st.id: int(st.is_approval_required) for st in models.ServiceType.objects.all()}

        if self.request.method == 'POST':

            context_data['hours_formset'] = forms.HoursFormset(
                self.request.POST,
                instance=self.object,
                prefix='hours'
            )
            context_data['followup_formset'] = forms.FollowupFormset(
                self.request.POST,
                instance=self.object,
                prefix='followup',
                form_kwargs={'service_event_instance': self.object, 'unit_field': self.request.POST.get('unit_field')}
            )
        else:
            context_data['hours_formset'] = forms.HoursFormset(instance=self.object, prefix='hours')
            context_data['followup_formset'] = forms.FollowupFormset(
                instance=self.object,
                prefix='followup',
                form_kwargs={
                    'service_event_instance': self.object,
                    'unit_field': (qa_models.TestListInstance.objects.get(pk=self.request.GET.get('ib')).unit_test_collection.unit if self.request.GET.get('ib') else None) if self.object is None else self.object.unit_service_area.unit
                }
            )

        return context_data

    def form_valid(self, form):

        context = self.get_context_data()
        hours_formset = context["hours_formset"]
        followup_formset = context["followup_formset"]

        if not hours_formset.is_valid() or not followup_formset.is_valid():
            return self.render_to_response(context)

        service_event = form.save()
        service_event_related = form.cleaned_data.get('service_event_related_field')
        try:
            sers = models.ServiceEvent.objects.filter(pk__in=service_event_related)
        except ValueError:
            sers = []
        service_event.service_event_related = sers

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

        for f_form in followup_formset:

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

        if 'is_approval_required_fake' in form.changed_data:
            form.changed_data.remove('is_approval_required_fake')

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

            if not form.instance.service_status.is_approval_required:
                form.instance.service_status = models.ServiceEventStatus.get_default()
                form.instance.datetime_status_changed = timezone.now()
                form.instance.user_status_changed_by = self.request.user

        return super(UpdateServiceEvent, self).form_valid(form)


class DetailsServiceEvent(DetailView):

    model = models.ServiceEvent
    template_name = 'service_log/service_event_detail.html'

    def get_context_data(self, **kwargs):
        context_data = super(DetailsServiceEvent, self).get_context_data(**kwargs)
        # context_data['service_event_tag_colours'] = models.ServiceEvent.get_colour_dict()
        context_data['hours'] = models.Hours.objects.filter(service_event=self.object)
        context_data['followups'] = models.QAFollowup.objects.filter(service_event=self.object)
        context_data['request'] = self.request
        context_data['g_links'] = models.GroupLinkerInstance.objects.filter(service_event=self.object)
        return context_data


def unit_sa_utc(request):

    unit = models.Unit.objects.get(id=request.GET['unit_id'])
    service_areas = list(models.ServiceArea.objects.filter(units=unit).values())

    testlist_ct = ContentType.objects.get(app_label="qa", model="testlist")
    utcs_tl_qs = models.UnitTestCollection.objects.filter(unit=unit, content_type=testlist_ct, active=True)
    utcs_tl = sorted([{'id': utc.id, 'name': utc.test_objects_name()} for utc in utcs_tl_qs], key=lambda utc: utc['name'])
    return JsonResponse({'service_areas': service_areas, 'utcs': utcs_tl})


def se_searcher(request):
    se_search = request.GET['q']
    unit_id = request.GET['unit_id']
    service_events = models.ServiceEvent.objects\
        .filter(id__icontains=se_search, unit_service_area__unit=unit_id) \
        .order_by('-id') \
        .select_related('service_status')[0:50]\
        .values_list('id', 'service_status__id')
    return JsonResponse({'colour_ids': list(service_events)})


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

    def __init__(self, *args, **kwargs):

        super(ServiceEventsBaseList, self).__init__(*args, **kwargs)
        self.templates = {
            'actions': get_template('service_log/table_context_se_actions.html'),
            'datetime_service': get_template('service_log/table_context_datetime.html'),
            'service_status__name': get_template('service_log/table_context_service_status.html'),
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
                to_return = to_return + ' - Approval is ' + ((not bool(int(val))) * 'not ') + 'required'

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
                    qs = qs.filter(is_approval_required=bool(int(val)))
                elif key == 'ss.ar':
                    qs = qs.filter(service_status__is_approval_required=bool(int(val)))
        return qs

    def format_col(self, field, obj):
        col = super(ServiceEventsBaseList, self).format_col(field, obj)
        return col

    def actions(self, se):
        template = self.templates['actions']
        mext = reverse('sl_list_all') + (('?f=' + self.kwarg_filters) if self.kwarg_filters else '')
        c = Context({'se': se, 'request': self.request, 'next': mext})
        return template.render(c)

    def datetime_service(self, se):
        template = self.templates['datetime_service']
        c = Context({'datetime': se.datetime_service})
        return template.render(c)

    # def problem_type__name(self, se):
    #     return se.problem_type.name if se.problem_type else ""

    def service_status__name(self, se):
        template = self.templates['service_status__name']
        c = Context({'service_status': se.service_status, 'request': self.request})
        return template.render(c)

    def problem_description(self, se):
        template = self.templates['problem_description']
        c = Context({'problem_description': se.problem_description, 'request': self.request})
        return template.render(c)


class QAFollowupsBaseList(BaseListableView):

    model = models.QAFollowup
    template_name = 'service_log/qafollowup_list.html'
    paginate_by = 50

    order_by = ['-datetime_assigned']
    kwarg_filters = None

    fields = (
        'actions',
        'pk',
        'datetime_assigned',
        'service_event__unit_service_area__unit__name',
        'unit_test_collection__tests_object__name',
        'test_list_instance_pass_fail',
        'test_list_instance_review_status',
        'service_event__service_status__name'
    )

    headers = {
        'pk': _('ID'),
        'datetime_assigned': _('Date Assigned'),
        'service_event__unit_service_area__unit__name': _('Unit'),
        'unit_test_collection__tests_object__name': _('Test List'),
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

    def __init__(self, *args, **kwargs):

        super(QAFollowupsBaseList, self).__init__(*args, **kwargs)
        self.templates = {
            'actions': get_template("service_log/table_context_qaf_actions.html"),
            'datetime_assigned': get_template("service_log/table_context_datetime.html"),
            'test_list_instance_pass_fail': get_template("qa/pass_fail_status.html"),
            'test_list_instance_review_status': get_template("qa/review_status.html"),
            'service_event__service_status__name': get_template("service_log/table_context_service_status.html"),
        }

    def get_icon(self):
        return 'fa-pencil-square-o'

    def get_page_title(self, f=None):
        if not f:
            return 'All QA Followups'
        to_return = 'QA Followups'
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
                    to_return += ' - Test List Reviewed'
                else:
                    to_return += ' - Test List Not Reviewed'
            elif key == 'ses.irr':
                to_return += ' - Service Event Status Not: '
                names = []
                for s in models.ServiceEventStatus.objects.filter(is_approval_required=False):
                    names.append(s.name)
                to_return += ','.join(names)

        return to_return

    def get(self, request, *args, **kwargs):
        if self.kwarg_filters is None:
            self.kwarg_filters = kwargs.pop('f', None)
        return super(QAFollowupsBaseList, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(QAFollowupsBaseList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        f = self.request.GET.get('f', False)
        context['kwargs'] = {'f': f} if f else {}
        context['page_title'] = self.get_page_title(f)
        return context

    def get_queryset(self):
        qs = super(QAFollowupsBaseList, self).get_queryset()

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
                    query_kwargs['service_event__service_status__is_approval_required'] = bool(int(val))

            qs = qs.filter(**query_kwargs)

        return qs

    def actions(self, qaf):
        template = self.templates['actions']
        mext = reverse('qaf_list_all') + (('?f=' + self.kwarg_filters) if self.kwarg_filters else '')
        c = Context({'qaf': qaf, 'request': self.request, 'next': mext, 'show_se_link': True})
        return template.render(c)

    def test_list_instance_pass_fail(self, qaf):
        template = self.templates['test_list_instance_pass_fail']
        c = Context({
            'instance': qaf.test_list_instance if qaf.test_list_instance else None,
            'show_dash': True,
            'exclude': ['no_tol'],
            'show_icons': True
        })
        return template.render(c)

    def test_list_instance_review_status(self, qaf):
        template = self.templates['test_list_instance_review_status']
        c = Context({
            "instance": qaf.test_list_instance if qaf.test_list_instance else None,
            "perms": PermWrapper(self.request.user),
            "request": self.request,
            'show_dash': True,
        })
        c.update(generate_review_status_context(qaf.test_list_instance))
        return template.render(c)

    def datetime_assigned(self, qaf):
        template = self.templates['datetime_assigned']
        c = Context({"datetime": qaf.datetime_assigned})
        return template.render(c)

    def service_event__service_status__name(self, qaf):
        template = self.templates['service_event__service_status__name']
        c = Context({"service_status": qaf.service_event.service_status, "request": self.request})
        return template.render(c)


class TLISelect(UTCInstances):

    qaf = None

    def get_page_title(self):
        try:
            utc = models.UnitTestCollection.objects.get(pk=self.kwargs["pk"])
            return "Select a %s instance" % utc.tests_object.name
        except:
            raise Http404

    def actions(self, tli):
        template = self.templates['actions']
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "select": True, 'f_form': self.kwargs['form']})
        return template.render(c)


def tli_statuses(request):
    tli = qa_models.TestListInstance.objects.get(pk=request.GET.get('tli_id'))
    return JsonResponse(
        {'pass_fail': tli.pass_fail_summary(), 'review': tli.review_summary(), 'datetime': timezone.localtime(tli.created)},
        safe=False
    )
