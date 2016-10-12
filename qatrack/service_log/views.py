
from django.contrib.auth.context_processors import PermWrapper
from django.core.urlresolvers import reverse, resolve
from django.forms.utils import timezone
from django.http import JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView

from listable.views import (
    BaseListableView, DATE_RANGE, SELECT_MULTI, NONEORNULL,
    TODAY, YESTERDAY, TOMORROW, LAST_WEEK, THIS_WEEK, NEXT_WEEK, LAST_14_DAYS, LAST_MONTH, THIS_MONTH, THIS_YEAR
)

from qatrack.service_log import models, forms


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

        print(to_return)

        return to_return

    def get_context_data(self, **kwargs):

        context = super(SLDashboard, self).get_context_data()
        context['counts'] = self.get_counts()

        return context


class CreateServiceEvent(CreateView):

    model = models.ServiceEvent
    # form_class = AuthorForm
    template_name = 'service_log/service_event.html'
    form_class = forms.ServiceEventForm

    def get_context_data(self, **kwargs):
        context_data = super(CreateServiceEvent, self).get_context_data(**kwargs)
        context_data['service_event_tag_colours'] = models.ServiceEvent.get_colour_dict()
        return context_data

    def form_valid(self, form):
        form.instance.user_created_by = self.request.user
        form.instance.datetime_created = timezone.now()
        return super(CreateServiceEvent, self).form_valid(form)

    def get_success_url(self):
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        return reverse("sl_dash")


class UpdateServiceEvent(UpdateView):

    model = models.ServiceEvent
    # form_class = AuthorForm
    template_name = 'service_log/service_event.html'
    form_class = forms.ServiceEventForm

    def get_context_data(self, **kwargs):
        context_data = super(UpdateServiceEvent, self).get_context_data(**kwargs)
        context_data['service_event_tag_colours'] = models.ServiceEvent.get_colour_dict()
        return context_data

    def form_valid(self, form):
        form.instance.user_modified_by = self.request.user
        form.instance.datetime_modified = timezone.now()
        return super(UpdateServiceEvent, self).form_valid(form)

    def get_success_url(self):

        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        return reverse("sl_dash")


class DetailsServiceEvent(DetailView):

    model = models.ServiceEvent
    template_name = 'service_log/service_event_detail.html'

    def get_context_data(self, **kwargs):
        context_data = super(DetailsServiceEvent, self).get_context_data(**kwargs)
        context_data['service_event_tag_colours'] = models.ServiceEvent.get_colour_dict()
        return context_data


def unit_service_areas(request):

    unit = models.Unit.objects.get(id=request.GET['unit_id'])
    service_areas = list(models.ServiceArea.objects.filter(units=unit).values())
    return JsonResponse({'service_areas': service_areas})


class ServiceEventsBaseList(BaseListableView):
    """
    This view provides a base for any sort of listing of
    :model:`service_log.ServiceEvent`'s.
    """

    model = models.ServiceEvent
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

    select_related = (
        "unit_service_area__unit",
        "unit_service_area__service_area"
    )

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
        print(col)
        return col

    def actions(self, se):
        template = self.templates['actions']
        c = Context({"se": se, "perms": PermWrapper(self.request.user), "request": self.request})
        return template.render(c)

    # def datetime_service(self, se):
    #     template = self.templates['datetime_service']
    #     c = Context({"datetime": se.datetime_service})
    #     return template.render(c)

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
    #
    # def work_completed(self, tli):
    #     template = self.templates['work_completed']
    #     c = Context({"instance": tli})
    #     return template.render(c)
    #
    # def review_status(self, tli):
    #     template = self.templates['review_status']
    #     c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request": self.request})
    #     c.update(generate_review_status_context(tli))
    #     return template.render(c)
    #
    # def pass_fail(self, tli):
    #     template = self.templates['pass_fail']
    #     c = Context({"instance": tli, "exclude": [models.NO_TOL], "show_label": True, "show_icons": settings.ICON_SETTINGS['SHOW_STATUS_ICONS_LISTING']})
    #     return template.render(c)