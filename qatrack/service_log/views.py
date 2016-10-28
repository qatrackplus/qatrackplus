
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse, resolve
from django.forms.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView

from listable.views import (
    BaseListableView, DATE_RANGE, SELECT_MULTI, NONEORNULL,
    TODAY, YESTERDAY, TOMORROW, LAST_WEEK, THIS_WEEK, NEXT_WEEK, LAST_14_DAYS, LAST_MONTH, THIS_MONTH, THIS_YEAR
)

from qatrack.service_log import models, forms
from qatrack.qa import models as qa_models


class SLDashboard(TemplateView):

    template_name = "service_log/sl_dash.html"

    def get_counts(self):

        # TODO: Parts low
        qs = models.QAFollowup.objects.filter(is_approved=False)
        to_return = {
            'qa_not_approved': qs.count(),
            'qa_not_complete': qs.filter(is_complete=False).count(),
            'units_restricted': models.Unit.objects.filter(restricted=True).count(),
            'parts_low': 0,
            'se_statuses': {}
        }

        qs = models.ServiceEventStatus.objects.filter(is_active=True)
        for s in qs:
            to_return['se_statuses'][s.name] = models.ServiceEvent.objects.filter(service_status=s).count()

        return to_return

    def get_context_data(self, **kwargs):

        context = super(SLDashboard, self).get_context_data()
        context['counts'] = self.get_counts()

        return context


class ServiceEventUpdateCreate(SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    """
    CreateView and UpdateView functionality combined
    """

    model = models.ServiceEvent
    # form_class = AuthorForm
    template_name = 'service_log/service_event_update.html'
    form_class = forms.ServiceEventForm

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
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context_data = super(ServiceEventUpdateCreate, self).get_context_data(**kwargs)
        context_data['service_event_tag_colours'] = models.ServiceEvent.get_colour_dict()
        context_data['status_tag_colours'] = models.ServiceEventStatus.get_colour_dict()

        # group_linkers = models.GroupLinker.objects.all()

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
                    'unit_field': None if self.object is None else self.object.unit_service_area.unit
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
        print('--- ServiceEventUpdateCreate.form_valid ---')

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

    def form_valid(self, form):

        self.instance = form.save(commit=False)
        form.instance.user_created_by = self.request.user
        form.instance.datetime_created = timezone.now()

        if form.cleaned_data['service_status'] is not models.ServiceEventStatus.get_default():
            form.instance.datetime_status_changed = timezone.now()
            form.instance.user_status_changed_by = self.request.user

        return super(CreateServiceEvent, self).form_valid(form)


class UpdateServiceEvent(ServiceEventUpdateCreate):

    def form_valid(self, form):

        self.instance = form.save(commit=False)
        form.instance.user_modified_by = self.request.user
        form.instance.datetime_modified = timezone.now()

        if 'service_status' in form.changed_data:
            form.instance.datetime_status_changed = timezone.now()
            form.instance.user_status_changed_by = self.request.user

        return super(UpdateServiceEvent, self).form_valid(form)


class DetailsServiceEvent(DetailView):

    model = models.ServiceEvent
    template_name = 'service_log/service_event_detail.html'

    def get_context_data(self, **kwargs):
        context_data = super(DetailsServiceEvent, self).get_context_data(**kwargs)
        context_data['service_event_tag_colours'] = models.ServiceEvent.get_colour_dict()
        context_data['hours'] = models.Hours.objects.filter(service_event=self.object)
        context_data['followups'] = models.QAFollowup.objects.filter(service_event=self.object)
        return context_data


def unit_sa_utc(request):

    unit = models.Unit.objects.get(id=request.GET['unit_id'])
    service_areas = list(models.ServiceArea.objects.filter(units=unit).values())

    testlist_ct = ContentType.objects.get(app_label="qa", model="testlist")
    utcs_tl_qs = models.UnitTestCollection.objects.filter(unit=unit, content_type=testlist_ct, active=True)
    utcs_tl = sorted([{'id': utc.id, 'name': utc.test_objects_name()} for utc in utcs_tl_qs], key=lambda utc: utc['name'])
    return JsonResponse({'service_areas': service_areas, 'utcs': utcs_tl})


class ServiceEventsBaseList(BaseListableView):
    """
    This view provides a base for any sort of listing of
    :model:`service_log.ServiceEvent`'s.
    """

    model = models.ServiceEvent
    template_name = 'service_log/service_event_list.html'
    paginate_by = 50

    order_by = ["-datetime_service"]

    fields = (
        "actions",
        "pk",
        "datetime_service",
        "unit_service_area__unit__name",
        "unit_service_area__service_area__name",
        "service_type__name",
        "problem_type__name",
        "problem_description",
        "service_status__name"
    )

    headers = {
        "pk": _("ID"),
        "datetime_service": _("Service Date"),
        "unit_service_area__unit__name": _("Unit"),
        "unit_service_area__service_area__name": _("Service Area"),
        "service_type__name": _("Service Type"),
        "problem_type__name": _("Problem Type"),
        "service_status__name": _("Service Status"),
    }

    widgets = {
        "datetime_service": DATE_RANGE,
        "unit_service_area__unit__name": SELECT_MULTI,
        "unit_service_area__service_area__name": SELECT_MULTI,
        "service_type__name": SELECT_MULTI,
        "problem_type__name": SELECT_MULTI,
        # "problem_description": False,
        "service_status__name": SELECT_MULTI
    }

    date_ranges = {
        "datetime_service": [TODAY, YESTERDAY, LAST_WEEK, THIS_WEEK, LAST_MONTH, THIS_MONTH, THIS_YEAR]
    }

    search_fields = {
        "actions": False,
    }

    order_fields = {
        "actions": False,
    }

    # select_related = (
    #     "unit_service_area__unit",
    #     "unit_service_area__service_area"
    # )

    # prefetch_related = ("testinstance_set", "testinstance_set__status")

    def __init__(self, *args, **kwargs):
        super(ServiceEventsBaseList, self).__init__(*args, **kwargs)

        self.templates = {
            'actions': get_template("service_log/table_context_se_actions.html"),
            'datetime_service': get_template("service_log/table_context_datetime.html"),
            'service_status__name': get_template("service_log/table_context_problem_type.html"),
            'problem_description': get_template("service_log/table_context_problem_description.html"),
        }

    def get_icon(self):
        return 'fa-wrench'

    def get_page_title(self):
        return "All Service Events"

    def get_context_data(self, *args, **kwargs):
        context = super(ServiceEventsBaseList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        context["page_title"] = self.get_page_title()
        return context

    def format_col(self, field, obj):
        col = super(ServiceEventsBaseList, self).format_col(field, obj)
        return col

    def actions(self, se):
        template = self.templates['actions']
        c = Context({"se": se, "perms": PermWrapper(self.request.user), "request": self.request})
        return template.render(c)

    def datetime_service(self, se):
        template = self.templates['datetime_service']
        c = Context({"datetime": se.datetime_service})
        return template.render(c)

    def problem_type__name(self, se):
        return se.problem_type.name if se.problem_type else ""

    def service_status__name(self, se):
        template = self.templates['service_status__name']
        c = Context({"service_status": se.service_status, "request": self.request})
        return template.render(c)

    def problem_description(self, se):
        template = self.templates['problem_description']
        c = Context({"problem_description": se.problem_description, "request": self.request})
        return template.render(c)
