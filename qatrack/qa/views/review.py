import calendar
import collections

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.generic import ListView, TemplateView, DetailView

from .. import models
from . import forms
from .base import TestListInstanceMixin, BaseEditTestListInstance, TestListInstances, UTCList
from .perform import ChooseUnit

from qatrack.units.models import Unit

from braces.views import PermissionRequiredMixin


#============================================================================
class TestListInstanceDetails(TestListInstanceMixin, DetailView):
    pass


#============================================================================
class ReviewTestListInstance(PermissionRequiredMixin, BaseEditTestListInstance):
    permission_required = "qa.can_review"
    form_class = forms.ReviewTestListInstanceForm
    formset_class = forms.ReviewTestInstanceFormSet
    template_name_suffix = "_review"

    #----------------------------------------------------------------------
    def form_valid(self, form):
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

        still_requires_review = False
        # for efficiency update statuses in bulk rather than test by test basis
        status_groups = collections.defaultdict(list)
        for ti_form in formset:
            status_pk = int(ti_form["status"].value())
            status_groups[status_pk].append(ti_form.instance.pk)

        for status_pk, test_instance_pks in status_groups.items():
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


#====================================================================================
class UTCReview(PermissionRequiredMixin, UTCList):
    permission_required = "qa.can_view_completed"
    action = "review"
    action_display = "Review"
    active_only = False

    #---------------------------------------------------------------------------
    def get_page_title(self):
        return "Review Test List Data"


#====================================================================================
class UTCFrequencyReview(UTCReview):

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""

        qs = super(UTCFrequencyReview, self).get_queryset()

        freq = self.kwargs["frequency"]
        self.frequencies = models.Frequency.objects.filter(slug__in=self.kwargs["frequency"].split("/"))

        q = Q(frequency__in=self.frequencies)
        if "ad-hoc" in freq:
            q |= Q(frequency=None)

        return qs.filter(q).distinct()

    #---------------------------------------------------------------------------
    def get_page_title(self):
        return " Review " + ", ".join([x.name for x in self.frequencies]) + " Test Lists"


#====================================================================================
class UTCUnitReview(UTCReview):

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""
        qs = super(UTCUnitReview, self).get_queryset()
        self.units = Unit.objects.filter(number__in=self.kwargs["unit_number"].split("/"))
        return qs.filter(unit__in=self.units).order_by("unit__number")

    #---------------------------------------------------------------------------
    def get_page_title(self):
        return "Review " + ", ".join([x.name for x in self.units]) + " Test Lists"


#====================================================================================
class ChooseUnitForReview(ChooseUnit):
    active_only = False
    template_name = "units/unittype_choose_for_review.html"


#====================================================================================
class ChooseFrequencyForReview(ListView):

    model = models.Frequency
    context_object_name = "frequencies"
    template_name_suffix = "_choose_for_review"


#============================================================================
class Unreviewed(TestListInstances):
    """view for grouping all test lists with a certain frequency for all units"""
    queryset = models.TestListInstance.objects.unreviewed

    #----------------------------------------------------------------------
    def get_page_title(self):
        return "Unreviewed Test Lists"


#============================================================================
class DueDateOverview(PermissionRequiredMixin, TemplateView):
    """Overall status of the QA Program"""
    template_name = "qa/overview_by_due_date.html"

    permission_required = "qa.can_review"

    DUE_DISPLAY_ORDER = (
        ("overdue", "Due & Overdue"),
        ("this_week", "Due This Week"),
        ("next_week", "Due Next Week"),
        ("this_month", "Due This Month"),
        ("next_month", "Due Next Month"),
    )

    #----------------------------------------------------------------------
    def get_queryset(self):

        qs = models.UnitTestCollection.objects.filter(
            active=True,
            visible_to__in=self.request.user.groups.all(),
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
            "tests_object",
        ).exclude(
            due_date=None
        ).order_by(
            "frequency__nominal_interval",
            "unit__number",
            "testlist__name",
            "testlistcycle__name",
        )

        return qs.distinct()

    #----------------------------------------------------------------------
    def get_context_data(self):
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
                due["this_month"].append(utc)  #pragma: nocover
            elif due_date <= next_month_end:
                due["next_month"].append(utc)

        ordered_due_lists = []
        for key, display in self.DUE_DISPLAY_ORDER:
            ordered_due_lists.append((display, due[key]))
        context["due"] = ordered_due_lists
        return context


#============================================================================
class Overview(PermissionRequiredMixin, TemplateView):
    """Overall status of the QA Program"""
    template_name = "qa/overview.html"

    permission_required = "qa.can_review"

    #----------------------------------------------------------------------
    def get_queryset(self):

        qs = models.UnitTestCollection.objects.filter(
            active=True,
            visible_to__in=self.request.user.groups.all(),
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
            "tests_object",
        ).order_by("frequency__nominal_interval", "unit__number", "testlist__name", "testlistcycle__name",)

        return qs.distinct()

    #----------------------------------------------------------------------
    def get_context_data(self):
        context = super(Overview, self).get_context_data()
        qs = self.get_queryset()

        units = Unit.objects.order_by("number")
        frequencies = list(models.Frequency.objects.order_by("nominal_interval")) + [None]

        unit_lists = []

        for unit in units:
            unit_lists.append((unit, []))
            for freq in frequencies:
                unit_lists[-1][-1].append((freq, [utc for utc in qs if utc.frequency == freq and utc.unit == unit]))

        context["unit_lists"] = unit_lists
        return context


#====================================================================================
class UTCInstances(TestListInstances):
    #----------------------------------------------------------------------
    def get_page_title(self):
        try:
            utc = models.UnitTestCollection.objects.get(pk=self.kwargs["pk"])
            return "History for %s" % utc.tests_object.name
        except:
            raise Http404

    #---------------------------------------------------------------------------
    def get_queryset(self):
        qs = super(UTCInstances, self).get_queryset()
        return qs.filter(unit_test_collection__pk=self.kwargs["pk"])
