import calendar
import collections

from braces.views import JSONResponseMixin, PermissionRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.generic import (
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    View,
)
import pytz

from qatrack.service_log.models import (
    ReturnToServiceQA,
    ServiceEvent,
    ServiceEventStatus,
    ServiceLog
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
        return context


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

        review_time = timezone.make_aware(timezone.datetime.now(), timezone.get_current_timezone())
        review_user = self.request.user

        test_list_instance = form.save(commit=False)
        initially_requires_reviewed = not test_list_instance.all_reviewed
        test_list_instance.reviewed = review_time
        test_list_instance.reviewed_by = review_user
        test_list_instance.all_reviewed = True
        test_list_instance.save()

        # note we are not calling if formset.is_valid() here since we assume
        # validity given we are only changing the status of the test_instances.
        # Also, we are not cleaning the data since a 500 will be raised if
        # something other than a valid int is passed for the status.
        #
        # If you add something here be very careful to check that the data
        # is clean before updating the db

        # for efficiency update statuses in bulk rather than test by test basis
        status_groups = collections.defaultdict(list)
        for ti_form in formset:
            status_pk = int(ti_form["status"].value())
            status_groups[status_pk].append(ti_form.instance.pk)

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

        if still_requires_review:
            test_list_instance.all_reviewed = False
            test_list_instance.save()

            if settings.USE_SERVICE_LOG:
                changed_se = test_list_instance.update_service_event_statuses()
                if len(changed_se) > 0:
                    messages.add_message(
                        request=self.request, level=messages.INFO,
                        message='Changed status of service event(s) %s to "%s".' % (
                            ', '.join(str(x) for x in changed_se),
                            ServiceEventStatus.get_default().name
                        )
                    )
        if settings.USE_SERVICE_LOG and initially_requires_reviewed != still_requires_review:
            for se in ServiceEvent.objects.filter(returntoserviceqa__test_list_instance=test_list_instance):
                ServiceLog.objects.log_rtsqa_changes(self.request.user, se)

        # Set utc due dates
        test_list_instance.unit_test_collection.set_due_date()

        # let user know request succeeded and return to unit list
        messages.add_message(
            request=self.request, message=_("Successfully updated %s " % self.object.test_list.name),
            level=messages.SUCCESS
        )
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
        return context


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
        return "Review Test List Data"


class UTCYourReview(PermissionRequiredMixin, UTCList):
    """A simple :view:`qa.base.UTCList` wrapper to check required review permissions"""

    permission_required = "qa.can_view_completed"
    raise_exception = True

    action = "review"
    action_display = "Review"

    def get_icon(self):
        return 'fa-users'

    def get_page_title(self):
        return "Review Your Test List Data"


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
        return " Review " + ", ".join([x.name for x in self.frequencies]) + " Test Lists"


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
        return "Review " + ", ".join([x.name for x in self.units]) + " Test Lists"


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
        return "Review All Inactive Test Lists"

    def get_icon(self):
        return 'fa-file'


class YourInactiveReview(UTCYourReview):

    visible_only = True
    active_only = False
    inactive_only = True

    def get_page_title(self):
        return "Review Your Inactive Test Lists"

    def get_icon(self):
        return 'fa-file'


class Unreviewed(PermissionRequiredMixin, TestListInstances):
    """Display all :model:`qa.TestListInstance`s with all_reviewed=False"""

    # queryset = models.TestListInstance.objects.unreviewed()
    permission_required = "qa.can_review"
    raise_exception = True

    def get_queryset(self):
        return models.TestListInstance.objects.unreviewed()

    def get_page_title(self):
        return "Unreviewed Test Lists"


class UnreviewedVisibleTo(Unreviewed):
    """Display all :model:`qa.TestListInstance`s with all_reviewed=False and unit_test_collection that is visible to
        the user"""

    def get_queryset(self):
        return models.TestListInstance.objects.your_unreviewed(self.request.user)

    def get_page_title(self):
        return "Unreviewed Test Lists Visible To Your Groups"


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
        return "Unreviewed Test Lists Visible To " + models.Group.objects.get(pk=self.kwargs['group']).name


class DueDateOverview(PermissionRequiredMixin, TemplateView):
    """View which :model:`qa.UnitTestCollection` are overdue & coming due"""

    template_name = "qa/overview_by_due_date.html"
    permission_required = ["qa.can_review", "qa.can_view_overview"]
    raise_exception = True

    DUE_DISPLAY_ORDER = (
        ("overdue", "Due & Overdue"),
        ("this_week", "Due This Week"),
        ("next_week", "Due Next Week"),
        ("this_month", "Due This Month"),
        ("next_month", "Due Next Month"),
    )

    def check_permissions(self, request):
        for perm in self.get_permission_required(request):
            if request.user.has_perm(perm):
                return True
        return False

    def get_queryset(self):

        qs = models.UnitTestCollection.objects.filter(
            active=True,
            unit__active=True,
            visible_to__in=self.request.user.groups.all(),
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
        next_month_start = month_end + timezone.timedelta(days=1)
        next_month_end = tz.localize(
            timezone.datetime(next_month_start.year, next_month_start.month, calendar.mdays[next_month_start.month])
        ).date()

        due = collections.defaultdict(list)

        units = set()
        freqs = set()

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
            freqs.add(str(utc.frequency or "Ad-Hoc"))

        ordered_due_lists = []
        for key, display in self.DUE_DISPLAY_ORDER:
            ordered_due_lists.append((key, display, due[key]))
        context["due"] = ordered_due_lists
        context["units"] = sorted(units)
        context["freqs"] = sorted(freqs)
        return context


class Overview(PermissionRequiredMixin, TemplateView):
    """Overall status of the QA Program"""

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
        context['title'] = 'Qa Program Overview'
        context['msg'] = 'Overview of current QA status on all units'
        if '-user' in self.request.path:
            context['title'] += ' For Your Groups'
            context['msg'] = 'Overview of current QA status (visible to your groups) on all units'
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
                freq_name = freq.name if freq else 'Ad Hoc'
                if freq_name not in unit_freqs:
                    unit_freqs[freq_name] = collections.OrderedDict()
                for utc in qs:
                    if utc.frequency == freq and utc.unit == unit:

                        if utc.last_instance:
                            last_instance_pfs = {}
                            for lipfs in utc.last_instance.pass_fail_status():
                                last_instance_pfs[lipfs[0]] = len(lipfs[2])
                        else:
                            last_instance_pfs = 'New List'

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

            unit_lists[unit.name] = unit_freqs

        return self.render_json_response({'unit_lists': unit_lists, 'due_counts': due_counts, 'success': True})


class UTCInstances(PermissionRequiredMixin, TestListInstances):
    """Show all :model:`qa.TestListInstance`s for a given :model:`qa.UnitTestCollection`"""

    permission_required = "qa.can_view_completed"

    def get_page_title(self):
        try:
            utc = models.UnitTestCollection.objects.get(pk=self.kwargs["pk"])
            return "History for %s :: %s" % (utc.unit.name, utc.name)
        except:
            raise Http404

    def get_queryset(self):
        qs = super(UTCInstances, self).get_queryset()
        return qs.filter(unit_test_collection__pk=self.kwargs["pk"])
