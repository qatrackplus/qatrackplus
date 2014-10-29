from .. import signals  # NOQA :signals import needs to be here so signals get registered

import logging
import collections

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.template import Context
from django.contrib.auth.context_processors import PermWrapper
from django.template.loader import get_template

from django.views.generic import UpdateView

from qatrack.qa import models

from qatrack.data_tables.views import BaseDataTablesDataSource

from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from listable.views import BaseListableView

logger = logging.getLogger('qatrack.console')


def generate_review_status_context(test_list_instance):

    if not test_list_instance:
        return {}

    statuses = collections.defaultdict(lambda: {"count": 0})
    comment_count = 0
    for ti in test_list_instance.testinstance_set.all():
        statuses[ti.status.name]["count"] += 1
        statuses[ti.status.name]["valid"] = ti.status.valid
        statuses[ti.status.name]["requires_review"] = ti.status.requires_review
        statuses[ti.status.name]["reviewed_by"] = test_list_instance.reviewed_by
        statuses[ti.status.name]["reviewed"] = test_list_instance.reviewed
        if ti.comment:
            comment_count += 1
    if test_list_instance.comment:
        comment_count += 1

    c = {"statuses": dict(statuses), "comments": comment_count, "show_icons": settings.ICON_SETTINGS['SHOW_REVIEW_ICONS']}

    return c


#============================================================================
class TestListInstanceMixin(SelectRelatedMixin, PrefetchRelatedMixin):
    """
    A mixin for commonly required prefetch_related/select_related  for
    :model:`qa.TestListInstance` views
    """

    model = models.TestListInstance
    context_object_name = "test_list_instance"

    prefetch_related = [
        "testinstance_set__unit_test_info",
        "testinstance_set__unit_test_info__test",
        "testinstance_set__reference",
        "testinstance_set__tolerance",
        "testinstance_set__status",
    ]
    select_related = [
        "unittestcollection",
        "unittestcollection__unit",
        "created_by",
        "modified_by",
        "test_list",
    ]


#============================================================================
class BaseEditTestListInstance(TestListInstanceMixin, UpdateView):
    """A common base for editing existing :model:`qa.TestListInstance`'s"""

    #----------------------------------------------------------------------
    def add_histories(self, forms):
        """paste historical values onto forms"""

        history, history_dates = self.object.history()
        self.history_dates = history_dates
        for f in forms:
            for instance, test_history in history:
                if f.instance == instance:
                    f.history = test_history

    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):

        context = super(BaseEditTestListInstance, self).get_context_data(**kwargs)

        # override the default queryset for the formset so that we can pull in all the
        # reference/tolerance data without the ORM generating lots of extra queries
        test_instances = self.object.testinstance_set.order_by("created").select_related(
            "status",
            "reference",
            "tolerance",
            "unit_test_info__test__category",
            "unit_test_info__unit",
        )

        if self.request.method == "POST":
            formset = self.formset_class(self.request.POST, self.request.FILES, instance=self.object, queryset=test_instances, user=self.request.user)
        else:
            formset = self.formset_class(instance=self.object, queryset=test_instances, user=self.request.user)

        self.add_histories(formset.forms)
        context["formset"] = formset
        context["history_dates"] = self.history_dates
        context["categories"] = set([x.unit_test_info.test.category for x in test_instances])
        context["statuses"] = models.TestInstanceStatus.objects.all()
        context["test_list"] = self.object.test_list
        context["unit_test_collection"] = self.object.unit_test_collection
        return context

    #----------------------------------------------------------------------
    def form_valid(self, form):
        """This view should always be subclassed"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def get_success_url(self):
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        return reverse("unreviewed")

class UTCList
#============================================================================
class UTCList(BaseDataTablesDataSource):
    """
    This view provides a base for any sort of listing of
    :model:`UnitTestCollection`'s.
    """

    model = models.UnitTestCollection
    action = "perform"
    action_display = "Perform"

    active_only = True

    initial_orderings = ["unit__number", "frequency__due_interval", "testlist__name", "testlistcycle__name"]

    def __init__(self, *args, **kwargs):
        super(UTCList, self).__init__(*args, **kwargs)

        # Store templates on view initialization so we don't have to reload them for every row!
        self.templates = {
            'actions': get_template("qa/unittestcollection_actions.html"),
            'work_completed': get_template("qa/testlistinstance_work_completed.html"),
            'review_status': get_template("qa/testlistinstance_review_status.html"),
            'pass_fail':  get_template("qa/pass_fail_status.html"),
            'due_date':  get_template("qa/due_date.html"),
        }

    #---------------------------------------------------------------------------
    def set_columns(self):
        """
        Setup the columns we want to be displayed for :model:`qa.UnitTestCollection`'s
        See :view:`data_tables.BaseDataTablesDataSource`.set_columns for more information
        """

        self.columns = (
            (self.get_actions, None, None),
            (
                lambda x: x.tests_object.name, (
                    ("testlist__name__icontains", ContentType.objects.get_for_model(models.TestList)),
                    ("testlistcycle__name__icontains", ContentType.objects.get_for_model(models.TestListCycle))
                ),
                ("testlist__name", "testlistcycle__name",)
            ),
            (self.get_due_date, None, None),
            (lambda x: x.unit.name, "unit__name__exact", "unit__number"),
            (lambda x: x.frequency.name if x.frequency else "Ad Hoc", "frequency", "frequency__due_interval"),

            (lambda x: x.assigned_to.name, "assigned_to__name__icontains", "assigned_to__name"),
            (self.get_last_instance_work_completed, None, "last_instance__work_completed"),
            (self.get_last_instance_pass_fail, None, None),
            (self.get_last_instance_review_status, None, None),
        )

    #----------------------------------------------------------------------
    def get_due_date(self, utc):
        template = self.templates['due_date']
        c = Context({"unit_test_collection": utc, "show_icons": settings.ICON_SETTINGS["SHOW_DUE_ICONS"]})
        return template.render(c)

    #----------------------------------------------------------------------
    def get_actions(self, utc):
        template = self.templates['actions']
        c = Context({"utc": utc, "request": self.request, "action": self.action})
        return template.render(c)

    #---------------------------------------------------------------------------
    def get_last_instance_work_completed(self, utc):
        template = self.templates['work_completed']
        c = Context({"instance": utc.last_instance})
        return template.render(c)

    #----------------------------------------------------------------------
    def get_last_instance_review_status(self, utc):
        template = self.templates['review_status']
        c = Context({"instance": utc.last_instance, "perms": PermWrapper(self.request.user), "request": self.request})
        c.update(generate_review_status_context(utc.last_instance))
        return template.render(c)

    #----------------------------------------------------------------------
    def get_last_instance_pass_fail(self, utc):
        template = self.templates['pass_fail']
        c = Context({"instance": utc.last_instance, "exclude": [models.NO_TOL], "show_label": True, "show_icons": settings.ICON_SETTINGS['SHOW_STATUS_ICONS_LISTING']})
        return template.render(c)

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset for visibility and fetch relevent related objects"""

        qs = super(UTCList, self).get_queryset().filter(
            visible_to__in=self.request.user.groups.all(),
        )

        if self.active_only:
            qs = qs.filter(active=True)

        qs = qs.select_related(
            "last_instance__work_completed",
            "last_instance__created_by",
            "frequency",
            "unit__name",
            "assigned_to__name",
        ).prefetch_related(
            "last_instance__testinstance_set",
            "last_instance__testinstance_set__status",
            "last_instance__reviewed_by",
            "last_instance__modified_by",
            "tests_object",
        )

        return qs.distinct()

    #----------------------------------------------------------------------
    def get_page_title(self):
        return "All Test Collections"

    #----------------------------------------------------------------------
    def get_template_context_data(self, context):

        context["page_title"] = self.get_page_title()
        context["action"] = self.action
        context["action_display"] = self.action_display
        return context


#============================================================================
class TestListInstances(BaseDataTablesDataSource):
    """
    This view provides a base for any sort of listing of
    :model:`qa.TestListInstance`'s.
    """

    model = models.TestListInstance
    queryset = models.TestListInstance.objects.all
    initial_orderings = ["unit_test_collection__unit__number", "-work_completed"]

    def __init__(self, *args, **kwargs):
        super(TestListInstances, self).__init__(*args, **kwargs)

        self.templates = {
            'actions': get_template("qa/testlistinstance_actions.html"),
            'work_completed': get_template("qa/testlistinstance_work_completed.html"),
            'review_status': get_template("qa/testlistinstance_review_status.html"),
            'pass_fail':  get_template("qa/pass_fail_status.html"),
        }

    #---------------------------------------------------------------------------
    def set_columns(self):
        """
        Setup the columns we want to be displayed for :model:`qa.TestListInstance`'s
        See :view:`data_tables.BaseDataTablesDataSource`.set_columns for more information
        """

        self.columns = (
            (self.get_actions, None, None),
            (lambda x: x.unit_test_collection.unit.name, "unit_test_collection__unit__name__exact", "unit_test_collection__unit__number"),
            (lambda x: x.unit_test_collection.frequency.name if x.unit_test_collection.frequency else "Ad-Hoc", "unit_test_collection__frequency", "unit_test_collection__frequency"),
            (lambda x: x.test_list.name, "test_list__name__icontains", "test_list__name"),
            (self.get_work_completed, None, "work_completed"),
            (lambda x: x.created_by.username, "created_by__username__icontains", "created_by__username"),
            (self.get_review_status, None, None),
            (self.get_pass_fail, None, None),
        )

    #----------------------------------------------------------------------
    def get_queryset(self):
        """fetch commonly used related objects"""

        return self.queryset().select_related(
            "test_list__name",
            "testinstance__status",
            "unit_test_collection__unit__name",
            "unit_test_collection__frequency__due_interval",
            "created_by", "modified_by", "reviewed_by",
        ).prefetch_related("testinstance_set", "testinstance_set__status")

    #----------------------------------------------------------------------
    def get_actions(self, tli):
        template = self.templates['actions']
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request": self.request})
        return template.render(c)

    #---------------------------------------------------------------------------
    def get_work_completed(self, tli):
        template = self.templates['work_completed']
        c = Context({"instance": tli})
        return template.render(c)

    #----------------------------------------------------------------------
    def get_review_status(self, tli):
        template = self.templates['review_status']
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request": self.request})
        c.update(generate_review_status_context(tli))
        return template.render(c)

    #----------------------------------------------------------------------
    def get_pass_fail(self, tli):
        template = self.templates['pass_fail']
        c = Context({"instance": tli, "exclude": [models.NO_TOL], "show_label": True, "show_icons": settings.ICON_SETTINGS['SHOW_STATUS_ICONS_LISTING']})
        return template.render(c)
