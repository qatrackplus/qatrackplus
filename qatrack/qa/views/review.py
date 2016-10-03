
import calendar
import collections
import json

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.generic import ListView, TemplateView, DetailView, View

from .. import models, utils
from . import forms
from .base import TestListInstanceMixin, BaseEditTestListInstance, TestListInstances, UTCList
from .perform import ChooseUnit

from qatrack.units.models import Unit

from braces.views import PermissionRequiredMixin, JSONResponseMixin


class TestListInstanceDetails(TestListInstanceMixin, DetailView):
    pass


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

        if still_requires_review:
            test_list_instance.all_reviewed = False
            test_list_instance.save()

        test_list_instance.unit_test_collection.set_due_date()

        # let user know request succeeded and return to unit list
        messages.success(self.request, _("Successfully updated %s " % self.object.test_list.name))
        return HttpResponseRedirect(self.get_success_url())


class UTCReview(PermissionRequiredMixin, UTCList):
    """A simple :view:`qa.base.UTCList` wrapper to check required review permissions"""

    permission_required = "qa.can_view_completed"
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
    template_name = "units/unittype_choose_for_review.html"


class ChooseFrequencyForReview(ListView):
    """Allow user to choose a :model:`qa.Frequency` to review :model:`qa.TestListInstance`s for"""

    model = models.Frequency
    context_object_name = "frequencies"
    template_name_suffix = "_choose_for_review"


class InactiveReview(UTCReview):

    active_only = False

    def get_page_title(self):
        print(self.page_title)
        return "Review All Inactive Test Lists"

    def get_icon(self):
        return 'fa-file'


class YourInactiveReview(UTCYourReview):

    visible_only = True
    active_only = False

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
        ).exclude(
            due_date=None
        ).extra(
            **utils.qs_extra_for_utc_name()
        ).order_by(
            "frequency__nominal_interval",
            "unit__number",
            "utc_name",
        )

        return qs.distinct()

    def get_context_data(self):
        """Group all active :model:`qa.UnitTestCollection` by due date category"""

        context = super(DueDateOverview, self).get_context_data()

        qs = self.get_queryset()

        now = timezone.now()
        today = now.date()
        friday = today + timezone.timedelta(days=(4 - today.weekday()) % 7)
        next_friday = friday + timezone.timedelta(days=7)
        month_end = timezone.datetime(now.year, now.month, calendar.mdays[now.month]).date()
        next_month_start = month_end + timezone.timedelta(days=1)
        next_month_end = timezone.datetime(next_month_start.year, next_month_start.month, calendar.mdays[next_month_start.month]).date()

        due = collections.defaultdict(list)

        for utc in qs:
            due_date = utc.due_date.date()
            if due_date <= today:
                due["overdue"].append(utc)
            elif due_date <= friday:
                if utc.last_instance is None or utc.last_instance.work_completed.date() != today:
                    due["this_week"].append(utc)
            elif due_date <= next_friday:
                due["next_week"].append(utc)
            elif due_date <= month_end:
                due["this_month"].append(utc)  # pragma: nocover
            elif due_date <= next_month_end:
                due["next_month"].append(utc)

        ordered_due_lists = []
        for key, display in self.DUE_DISPLAY_ORDER:
            ordered_due_lists.append((display, due[key]))
        context["due"] = ordered_due_lists
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


class OverviewObjects(JSONResponseMixin, View):

    def get_queryset(self):

        qs = models.UnitTestCollection.objects.filter(
            active=True,
            # visible_to__in=self.request.user.groups.all(),
        ).select_related(
            "last_instance__work_completed",
            "last_instance__created_by",
            "frequency",
            "unit__name",
            "assigned_to__name",
        ).prefetch_related(
            "last_instance__testinstance_set",
            "last_instance__testinstance_set__status",
            "last_instance__modified_by",
        ).extra(
            **utils.qs_extra_for_utc_name()
        ).order_by("frequency__nominal_interval", "unit__number", "utc_name", )

        return qs.distinct()

    def get(self, request):

        qs = self.get_queryset()

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
                        unit_freqs[freq_name][utc.utc_name] = {
                            'id': utc.pk,
                            'url': reverse('review_utc', args=(utc.pk,)),
                            'last_instance_status': last_instance_pfs,
                            'last_instance_work_completed': utc.last_instance.work_completed if utc.last_instance else None,
                            'due_date': utc.due_date,
                            'due_status': ds
                        }
                        due_counts[ds] += 1
            # print unit_freqs
            unit_lists[unit.name] = unit_freqs

        return self.render_json_response({'unit_lists': unit_lists, 'due_counts': due_counts, 'success': True})


class UTCInstances(TestListInstances):
    """Show all :model:`qa.TestListInstance`s for a given :model:`qa.UnitTestCollection`"""

    def get_page_title(self):
        try:
            utc = models.UnitTestCollection.objects.get(pk=self.kwargs["pk"])
            return "History for %s" % utc.tests_object.name
        except:
            raise Http404

    def get_queryset(self):
        qs = super(UTCInstances, self).get_queryset()
        return qs.filter(unit_test_collection__pk=self.kwargs["pk"])
