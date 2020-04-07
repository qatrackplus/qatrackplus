import calendar
import collections

from braces.views import JSONResponseMixin, PermissionRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.transaction import atomic
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import (
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    View,
)
import pytz

from qatrack.qatrack_core.utils import format_datetime
from qatrack.reports.reports import UTCReport
from qatrack.service_log.models import (
    ReturnToServiceQA,
    ServiceEvent,
    ServiceEventStatus,
    ServiceLog,
)
from qatrack.units.models import Unit

from . import forms
from .. import models
from .base import (
    BaseEditTestListInstance,
    TestListInstanceMixin,
    TestListInstances,
    UTCList,
)
from .perform import ChooseUnit


class TestListInstanceDetails(PermissionRequiredMixin, TestListInstanceMixin, DetailView):

    permission_required = "qa.can_view_completed"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(kwargs=kwargs)

        rtsqas = ReturnToServiceQA.objects.filter(test_list_instance=self.object)
        se_rtsqa = []
        for f in rtsqas:
            if f.service_event not in se_rtsqa:
                se_rtsqa.append(f.service_event)

        context['service_events_rtsqa'] = se_rtsqa

        se_ib = ServiceEvent.objects.filter(test_list_instance_initiated_by=self.object)
        context['service_events_ib'] = se_ib
        self.all_tests = self.object.test_list.ordered_tests()
        context['borders'] = self.object.test_list.sublist_borders(self.all_tests)

        if self.object.unit_test_collection.tests_object.__class__.__name__ == 'TestListCycle':
            context['cycle_name'] = self.object.unit_test_collection.name
        return context


def test_list_instance_report(request, pk):

    tli = get_object_or_404(models.TestListInstance, id=pk)
    utc = tli.unit_test_collection
    wc = format_datetime(tli.work_completed)

    base_opts = {
        'report_type': UTCReport.report_type,
        'report_format': request.GET.get("type", "pdf"),
        'title': "%s - %s - %s" % (utc.unit.name, tli.test_list.name, wc),
        'include_signature': False,
        'visible_to': [],
    }

    report_opts = {
        'work_completed': "%s - %s" % (wc, wc),
        'unit_test_collection': [utc.id],
    }
    report = UTCReport(base_opts=base_opts, report_opts=report_opts, user=request.user)

    return report.render_to_response(base_opts['report_format'])


class ReviewTestListInstance(PermissionRequiredMixin, BaseEditTestListInstance):
    """
    This views main purpose is for reviewing a completed :model:`qa.TestListInstance`
    and updating the :model:`qa.TestInstance`s :model:`qa.TestInstanceStatus`
    """

    permission_required = "qa.can_review"
    raise_exception = True

    form_class = forms.ReviewTestListInstanceForm
    formset_class = forms.ReviewTestInstanceFormSet
    template_name_suffix = "_review"

    rtsqa_form = None
    from_se = False

    def get_form_kwargs(self):
        kwargs = super(ReviewTestListInstance, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """
        Update users, times & statuses for the :model:`qa.TestListInstance`
        and :model:`qa.TestInstance`s. TestListInstances all_reviewed is also
        set.
        """

        context = self.get_context_data()
        formset = context["formset"]

        test_list_instance = form.save(commit=False)
        statuses = []
        test_instances = []

        # note we are not calling if formset.is_valid() here since we assume
        # validity given we are only changing the status of the test_instances.
        # Also, we are not cleaning the data since a 500 will be raised if
        # something other than a valid int is passed for the status.
        #
        # If you add something here be very careful to check that the data
        # is clean before updating the db
        for ti_form in formset:
            status_pk = int(ti_form["status"].value())
            statuses.append(status_pk)
            test_instances.append(ti_form.instance)

        changed_se = review_test_list_instance(test_list_instance, test_instances, statuses, self.request.user)

        if settings.USE_SERVICE_LOG:
            if len(changed_se) > 0 and self.from_se:
                msg = _(
                    'Changed status of service event(s) %(service_event_ids)s to "%(serviceeventstatus_name)s".'
                ) % {
                    'service_event_ids': ', '.join(str(x) for x in changed_se),
                    'serviceeventstatus_name': ServiceEventStatus.get_default().name,
                }
                messages.add_message(request=self.request, level=messages.INFO, message=msg)

        if self.from_se:
            return JsonResponse({'rtsqa_form': self.rtsqa_form, 'tli_id': test_list_instance.id})

        # let user know request succeeded and return to unit list
        msg = _("Successfully updated %(test_list_name)s") % {'test_list_name': self.object.test_list.name}
        messages.add_message(request=self.request, message=msg, level=messages.SUCCESS)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(ReviewTestListInstance, self).get_context_data(kwargs=kwargs)

        rtsqas = ReturnToServiceQA.objects.filter(test_list_instance=self.object)
        se = []
        for f in rtsqas:
            if f.service_event not in se:
                se.append(f.service_event)

        context['service_events'] = se
        tests = [f.instance.unit_test_info.test for f in context['formset']]
        context['borders'] = self.object.test_list.sublist_borders(tests)
        context['cycle_ct'] = ContentType.objects.get_for_model(models.TestListCycle).id

        self.rtsqa_form = self.kwargs.get('rtsqa_form')
        self.from_se = self.rtsqa_form is not None
        context['rtsqa_form'] = self.rtsqa_form
        context['from_se'] = self.from_se

        return context


@atomic
def review_test_list_instance(test_list_instance, test_instances, status_pks, review_user):
    """Common code for reviewing test list instances from the ReviewTestListInstance and
    bulk_review views.

    test_list_instance is the TLI to be reviewed

    test_instances is the set of test_instances belonging to test_list_instance
    status_pks is a list of status ids, the same length as test_instances, to be applied to each
    of the corresponding test instances (i.e. the Nth status id will be applied to the Nth test instance.

    review_user is the user who performed the review
    """

    review_time = timezone.make_aware(timezone.datetime.now(), timezone.get_current_timezone())

    initially_requires_reviewed = not test_list_instance.all_reviewed
    test_list_instance.reviewed = review_time
    test_list_instance.reviewed_by = review_user
    test_list_instance.all_reviewed = True
    test_list_instance.save()

    # for efficiency update statuses in bulk rather than test by test basis
    status_groups = collections.defaultdict(list)
    for instance, status_pk in zip(test_instances, status_pks):
        status_groups[status_pk].append(instance.pk)

    still_requires_review = False
    for status_pk, test_instance_pks in list(status_groups.items()):
        status = models.TestInstanceStatus.objects.get(pk=status_pk)
        if status.requires_review:
            still_requires_review = True
        models.TestInstance.objects.filter(pk__in=test_instance_pks).update(status=status)

    # Handle Service Log items:
    #
    #    Change status of service events with status__requires_review = False to have default status if this
    #    test_list still requires approval.
    #
    #    Log changes to this test_list_instance review status if linked to service_events via rtsqa.
    changed_se = []
    if still_requires_review:
        test_list_instance.all_reviewed = False
        test_list_instance.save()

        if settings.USE_SERVICE_LOG:
            changed_se = test_list_instance.update_service_event_statuses()

    if settings.USE_SERVICE_LOG and initially_requires_reviewed != still_requires_review:
        for se in ServiceEvent.objects.filter(returntoserviceqa__test_list_instance=test_list_instance):
            ServiceLog.objects.log_rtsqa_changes(review_user, se)

    # Set utc due dates
    test_list_instance.unit_test_collection.set_due_date()

    return changed_se


class TestListInstanceDelete(PermissionRequiredMixin, DeleteView):
    """
    This view is for deleting a :model:`qa.TestListInstance`
    """

    permission_required = "qa.delete_testlistinstance"
    raise_exception = True

    model = models.TestListInstance

    def get_success_url(self):
        return self.request.GET.get("next", reverse("home"))

    def delete(self, request, *args, **kwargs):
        service_events = ServiceEvent.objects.filter(returntoserviceqa__test_list_instance_id=kwargs['pk'])
        delete = super().delete(request, *args, **kwargs)
        for se in service_events:
            ServiceLog.objects.log_rtsqa_changes(request.user, se)
        return delete


class UTCReview(PermissionRequiredMixin, UTCList):
    """A simple :view:`qa.base.UTCList` wrapper to check required review permissions"""

    permission_required = "qa.can_review"
    raise_exception = True

    action = "review"
    action_display = "Review"
    visible_only = False

    def get_icon(self):
        return 'fa-users'

    def get_page_title(self):
        return _("Review Test List Data")


class UTCYourReview(PermissionRequiredMixin, UTCList):
    """A simple :view:`qa.base.UTCList` wrapper to check required review permissions"""

    permission_required = "qa.can_view_completed"
    raise_exception = True

    action = "review"
    action_display = _l("Review")

    def get_icon(self):
        return 'fa-users'

    def get_page_title(self):
        return _("Review Your Test List Data")


class UTCFrequencyReview(UTCYourReview):
    """A simple :view:`qa.review.UTCReview` wrapper to filter by :model:`qa.Frequency`"""

    def get_queryset(self):
        """filter queryset by frequency"""

        qs = super(UTCFrequencyReview, self).get_queryset()

        freq = self.kwargs["frequency"]
        self.frequencies = models.Frequency.objects.filter(slug__in=self.kwargs["frequency"].split("/"))

        q = Q(frequency__in=self.frequencies)
        if "ad-hoc" in freq:
            q |= Q(frequency=None)

        return qs.filter(q).distinct()

    def get_icon(self):
        return 'fa-clock-o'

    def get_page_title(self):
        return _(" Review %(frequency_names)s Test Lists") % {
            'frequency_names': ", ".join([x.name for x in self.frequencies])
        }


class UTCUnitReview(UTCYourReview):
    """A simple :view:`qa.review.UTCReview` wrapper to filter by :model:`units.Unit`"""

    def get_queryset(self):
        """filter queryset by frequency"""
        qs = super(UTCUnitReview, self).get_queryset()
        self.units = Unit.objects.filter(number__in=self.kwargs["unit_number"].split("/"))
        return qs.filter(unit__in=self.units).order_by("unit__number")

    def get_icon(self):
        return 'fa-cube'

    def get_page_title(self):
        return _(" Review %(unit_names)s Test Lists") % {'unit_names': ", ".join([x.name for x in self.units])}


class ChooseUnitForReview(ChooseUnit):
    """Allow user to choose a :model:`units.Unit` to review :model:`qa.TestListInstance`s for"""

    active_only = True
    template_name = 'units/unittype_choose_for_review.html'
    # template_name = 'units/unittype_list.html'


class ChooseFrequencyForReview(ListView):
    """Allow user to choose a :model:`qa.Frequency` to review :model:`qa.TestListInstance`s for"""

    model = models.Frequency
    context_object_name = "frequencies"
    template_name_suffix = "_choose_for_review"


class InactiveReview(UTCReview):

    active_only = False
    inactive_only = True

    def get_page_title(self):
        return _("Review All Inactive Test Lists")

    def get_icon(self):
        return 'fa-file'


class YourInactiveReview(UTCYourReview):

    visible_only = True
    active_only = False
    inactive_only = True

    def get_page_title(self):
        return _("Review Your Inactive Test Lists")

    def get_icon(self):
        return 'fa-file'


class Unreviewed(PermissionRequiredMixin, TestListInstances):
    """Display all :model:`qa.TestListInstance`s with all_reviewed=False"""

    fields = (
        "actions",
        "unit_test_collection__unit__name",
        "unit_test_collection__frequency__name",
        "test_list__name",
        "work_completed",
        "created_by__username",
        "review_status",
        "pass_fail",
    )

    headers = {
        "unit_test_collection__unit__name": _("Unit"),
        "unit_test_collection__frequency__name": _("Frequency"),
        "created_by__username": _("Created By"),
    }

    search_fields = {
        "actions": False,
        "pass_fail": False,
        "review_status": False,
        "bulk_review_status": False,
    }

    order_fields = {
        "actions": False,
        "unit_test_collection__unit__name": "unit_test_collection__unit__number",
        "unit_test_collection__frequency__name": "unit_test_collection__frequency__nominal_interval",
        "review_status": False,
        "pass_fail": False,
        "bulk_review_status": False,
        "selected": False,
    }

    if settings.REVIEW_BULK:
        fields = fields + ("bulk_review_status", "selected")
        headers["selected"] = mark_safe(
            '<input type="checkbox" class="test-selected-toggle" title="%s"/>' % _("Select All")
        )
        headers["bulk_review_status"] = lambda: Unreviewed._status_select(header=True)
        search_fields["selected"] = False
        order_fields["selected"] = False

    permission_required = "qa.can_review"
    raise_exception = True

    @classmethod
    def _status_select(cls, header=False):
        if header:
            title = _("Select the review status to apply to all currently selected test instance rows")
        else:
            title = _("Select the review status to apply to this row")

        return get_template("qa/_testinstancestatus_select.html").render({
            'name': 'bulk-status' if header else '',
            'id': 'bulk-status' if header else '',
            'statuses': models.TestInstanceStatus.objects.all(),
            'class': 'input-medium' + (' bulk-status' if header else ''),
            'title': title,
        })

    def selected(self, obj):
        return '<input type="checkbox" class="test-selected" title="%s"/>' % _(
            "Check to include this test list instance when bulk setting approval statuses"
        )

    def bulk_review_status(self, obj):
        if not hasattr(self, "_bulk_review"):
            self._bulk_review = self._status_select()

        return self._bulk_review.replace(":TLI_ID:", str(obj.pk))

    def get_queryset(self):
        return models.TestListInstance.objects.unreviewed()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['bulk_review'] = settings.REVIEW_BULK
        return context

    def get_page_title(self):
        return _("Unreviewed Test List Instances")


def bulk_review(request):

    count = 0
    for pairs in request.POST.getlist('tlis'):
        status, tli = pairs.split(",")
        tli = models.TestListInstance.objects.get(pk=tli)
        test_instances = tli.testinstance_set.all()
        statuses = [status] * len(test_instances)
        review_test_list_instance(tli, test_instances, statuses, request.user)
        count += 1

    msg = _("Successfully reviewed %(count)s test list instances") % {'count': count}
    messages.add_message(request=request, message=msg, level=messages.SUCCESS)
    return JsonResponse({"ok": True})


class UnreviewedVisibleTo(Unreviewed):
    """Display all :model:`qa.TestListInstance`s with all_reviewed=False and unit_test_collection that is visible to
        the user"""

    def get_queryset(self):
        return models.TestListInstance.objects.your_unreviewed(self.request.user)

    def get_page_title(self):
        return _("Unreviewed Test List Instances Visible To Your Groups")


class ChooseGroupVisibleTo(ListView):

    active_only = False
    template_name = "qa/group_choose_visible_to.html"
    model = models.Group
    context_object_name = "groups"


class UnreviewedByVisibleToGroup(Unreviewed):
    """Display all :model:`qa.TestListInstance`s with all_reviewed=False and unit_test_collection that is visible to
        a select :model:`auth.Group`
    """

    def get_queryset(self):
        qs = super(UnreviewedByVisibleToGroup, self).get_queryset()
        return qs.filter(unit_test_collection__visible_to=self.kwargs['group'])

    def get_icon(self):
        return 'fa-users'

    def get_page_title(self):
        return _("Unreviewed Test List Instances Visible To %(group_name)s") % {
            'group_name': models.Group.objects.get(pk=self.kwargs['group']).name
        }


class DueDateOverview(PermissionRequiredMixin, TemplateView):
    """View which :model:`qa.UnitTestCollection` are overdue & coming due"""

    template_name = "qa/overview_by_due_date.html"
    permission_required = ["qa.can_review", "qa.can_view_overview", 'qa.can_review_non_visible_tli']
    raise_exception = True

    DUE_DISPLAY_ORDER = (
        ("overdue", _l("Due & Overdue")),
        ("this_week", _l("Due This Week")),
        ("next_week", _l("Due Next Week")),
        ("this_month", _l("Due This Month")),
        ("next_month", _l("Due Next Month")),
    )

    def check_permissions(self, request):
        for perm in self.get_permission_required(request):
            if request.user.has_perm(perm):
                return True
        return False

    def get_queryset(self):

        qs = models.UnitTestCollection.objects.filter(
            active=True,
            unit__active=True
        ).select_related(
            "last_instance",
            "frequency",
            "unit",
            "assigned_to",
        ).prefetch_related(
            "last_instance__testinstance_set",
            "last_instance__testinstance_set__status",
            "last_instance__modified_by",
            "tests_object",
        ).exclude(due_date=None).order_by(
            "frequency__nominal_interval",
            "unit__number",
            "name",
        )

        return qs.distinct()

    def get_context_data(self):
        """Group all active :model:`qa.UnitTestCollection` by due date category"""

        context = super(DueDateOverview, self).get_context_data()

        qs = self.get_queryset()

        tz = pytz.timezone(settings.TIME_ZONE)
        now = timezone.now().astimezone(tz)
        today = now.date()
        friday = today + timezone.timedelta(days=(4 - today.weekday()) % 7)
        next_friday = friday + timezone.timedelta(days=7)
        month_end = tz.localize(timezone.datetime(now.year, now.month, calendar.mdays[now.month])).date()
        if calendar.isleap(now.year) and now.month == 2:
            month_end += timezone.timedelta(days=1)
        next_month_start = month_end + timezone.timedelta(days=1)
        next_month_end = tz.localize(
            timezone.datetime(next_month_start.year, next_month_start.month, calendar.mdays[next_month_start.month])
        ).date()

        due = collections.defaultdict(list)

        units = set()
        freqs = set()
        groups = set()

        for utc in qs:
            due_date = utc.due_date.astimezone(tz).date()
            if due_date <= today:
                due["overdue"].append(utc)
            elif due_date <= friday:
                if utc.last_instance is None or utc.last_instance.work_completed.astimezone(tz).date() != today:
                    due["this_week"].append(utc)
            elif due_date <= next_friday:
                due["next_week"].append(utc)
            elif due_date <= month_end:
                due["this_month"].append(utc)  # pragma: nocover
            elif due_date <= next_month_end:
                due["next_month"].append(utc)

            units.add(str(utc.unit))
            freqs.add(str(utc.frequency or _("Ad-Hoc")))
            groups.add(str(utc.assigned_to))

        ordered_due_lists = []
        for key, display in self.DUE_DISPLAY_ORDER:
            ordered_due_lists.append((key, display, due[key]))
        context["due"] = ordered_due_lists
        context["units"] = sorted(units)
        context["freqs"] = sorted(freqs)
        context["groups"] = sorted(groups)
        context['user_groups'] = '-user' in self.request.path

        return context


class DueDateOverviewUser(DueDateOverview):

    permission_required = ["qa.can_review", "qa.can_view_overview"]

    def get_queryset(self):
        return super().get_queryset().filter(visible_to__in=self.request.user.groups.all())


class Overview(PermissionRequiredMixin, TemplateView):
    """Overall status of the QC Program"""

    template_name = "qa/overview.html"
    permission_required = ["qa.can_review", "qa.can_view_overview"]
    raise_exception = True

    def check_permissions(self, request):
        for perm in self.get_permission_required(request):
            if request.user.has_perm(perm):
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super(Overview, self).get_context_data()
        context['title'] = _('QC Program Overview')
        context['msg'] = _('Overview of current QC status on all units')
        if '-user' in self.request.path:
            context['title'] = _('QC Program Overview For Your Groups')
            context['msg'] = _('Overview of current QC status (visible to your groups) on all units')
            context['user_groups'] = True
        return context


class OverviewObjects(JSONResponseMixin, View):

    def get_queryset(self, request):

        qs = models.UnitTestCollection.objects.filter(
            active=True,
            unit__active=True,
        ).select_related(
            "last_instance",
            "frequency",
            "unit",
            "assigned_to",
        ).prefetch_related(
            "last_instance__testinstance_set",
            "last_instance__testinstance_set__status",
            "last_instance__modified_by",
        ).order_by("frequency__nominal_interval", "unit__number", "name", )

        if request.GET.get('user') == 'true':
            qs = qs.filter(visible_to__in=request.user.groups.all())

        return qs.distinct()

    def get(self, request):

        qs = self.get_queryset(request)

        units = Unit.objects.order_by("number")
        frequencies = list(models.Frequency.objects.order_by("nominal_interval")) + [None]

        unit_lists = collections.OrderedDict()
        due_counts = {'ok': 0, 'tolerance': 0, 'action': 0, 'no_tol': 0}

        for unit in units:
            unit_freqs = collections.OrderedDict()
            for freq in frequencies:
                freq_name = freq.name if freq else _('Ad Hoc')
                if freq_name not in unit_freqs:
                    unit_freqs[freq_name] = collections.OrderedDict()
                for utc in qs:
                    if utc.frequency == freq and utc.unit == unit:

                        if utc.last_instance:
                            last_instance_pfs = {}
                            for lipfs in utc.last_instance.pass_fail_status():
                                last_instance_pfs[lipfs[0]] = len(lipfs[2])
                        else:
                            last_instance_pfs = _('New List')

                        ds = utc.due_status()
                        last_completed = utc.last_instance.work_completed if utc.last_instance else None
                        unit_freqs[freq_name][utc.name] = {
                            'id': utc.pk,
                            'url': reverse('review_utc', args=(utc.pk,)),
                            'last_instance_status': last_instance_pfs,
                            'last_instance_work_completed': last_completed,
                            'due_date': utc.due_date,
                            'due_status': ds
                        }
                        due_counts[ds] += 1

            unit_lists[unit.number] = {'unit_freqs': unit_freqs, 'unit_name': unit.name, 'unit_id': unit.id}

        return self.render_json_response({'unit_lists': unit_lists, 'due_counts': due_counts, 'success': True})


class UTCInstances(PermissionRequiredMixin, TestListInstances):
    """Show all :model:`qa.TestListInstance`s for a given :model:`qa.UnitTestCollection`"""

    permission_required = "qa.can_view_completed"

    def get_page_title(self):
        try:
            utc = models.UnitTestCollection.objects.get(pk=self.kwargs["pk"])
            return _("History for %(unit_name)s :: %(unit_test_collection_name)s") % {
                'unit_name': utc.unit.name,
                'unit_test_collection_name': utc.name
            }
        except models.UnitTestCollection.DoesNotExist:
            raise Http404

    def get_queryset(self):
        qs = super(UTCInstances, self).get_queryset()
        return qs.filter(unit_test_collection__pk=self.kwargs["pk"])
