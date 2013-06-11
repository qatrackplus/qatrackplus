from .. import signals  # signals import needs to be here so signals get registered

import json
import logging
import urllib


from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.template import Context
from django.contrib.auth.context_processors import PermWrapper
from django.template.loader import get_template

from django.views.generic import ListView, UpdateView
from django.utils import timezone

from qatrack.qa import models, utils
from qatrack.qa.templatetags import qa_tags

from qatrack.data_tables.views import BaseDataTablesDataSource

from braces.views import PermissionRequiredMixin, PrefetchRelatedMixin, SelectRelatedMixin

logger = logging.getLogger('qatrack.console')

class TestListInstanceMixin(SelectRelatedMixin, PrefetchRelatedMixin):

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


    #----------------------------------------------------------------------
    def add_histories(self, forms):
        """paste historical values onto forms"""

        history, history_dates = self.object.history()
        self.history_dates = history_dates
        for (instance, test_history), f in zip(history, forms):
            f.history = test_history

    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):

        context = super(BaseEditTestListInstance, self).get_context_data(**kwargs)

        # override the default queryset for the formset so that we can pull in all the
        # reference/tolerance data without the ORM generating lots of extra queries
        test_instances = self.object.testinstance_set.select_related(
            "status",
            "reference",
            "tolerance",
            "unit_test_info__test__category",
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
        raise NotImplementedError

    #----------------------------------------------------------------------
    def get_success_url(self):
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        return reverse("unreviewed")


#============================================================================
class UTCList(BaseDataTablesDataSource):
    model = models.UnitTestCollection
    action = "perform"
    action_display = "Perform"

    initial_orderings = ["unit__number", "frequency__due_interval", "testlist__name", "testlistcycle__name"]

    #---------------------------------------------------------------------------
    def set_columns(self):
        self.columns = (
            (self.get_actions, None, None),
            (
                lambda x: x.tests_object.name, (
                    ("testlist__name__icontains", ContentType.objects.get_for_model(models.TestList)),
                    ("testlistcycle__name__icontains", ContentType.objects.get_for_model(models.TestListCycle))
                ),
                ("testlist__name", "testlistcycle__name",)
            ),
            (qa_tags.as_due_date, None, None),
            (lambda x: x.unit.name, "unit__name__exact", "unit__number"),
            (lambda x: x.frequency.name if x.frequency else "Ad Hoc", "frequency", "frequency__due_interval"),

            (lambda x: x.assigned_to.name, "assigned_to__name__icontains", "assigned_to__name"),
            (self.get_last_instance_work_completed, None, "last_instance__work_completed"),
            (self.get_last_instance_pass_fail, None, None),
            (self.get_last_instance_review_status, None, None),
        )

    #----------------------------------------------------------------------
    def get_actions(self, utc):
        template = get_template("qa/unittestcollection_actions.html")
        c = Context({"utc": utc, "request": self.request, "action": self.action})
        return template.render(c)

    #---------------------------------------------------------------------------
    def get_last_instance_work_completed(self, utc):
        template = get_template("qa/testlistinstance_work_completed.html")
        c = Context({"instance": utc.last_instance})
        return template.render(c)

    #----------------------------------------------------------------------
    def get_last_instance_review_status(self, utc):
        template = get_template("qa/testlistinstance_review_status.html")
        c = Context({"instance": utc.last_instance, "perms": PermWrapper(self.request.user), "request": self.request})
        return template.render(c)

    #----------------------------------------------------------------------
    def get_last_instance_pass_fail(self, utc):
        return qa_tags.as_pass_fail_status(utc.last_instance)

    #----------------------------------------------------------------------
    def get_queryset(self):

        qs = super(UTCList, self).get_queryset().filter(
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
        )

        return qs.distinct()

    #----------------------------------------------------------------------
    def get_page_title(self):
        return "All Test Collections"

    #----------------------------------------------------------------------
    def get_template_context_data(self, context):
        # context = super(UTCList,self).get_context_data(*args,**kwargs)
        context["page_title"] = self.get_page_title()
        context["action"] = self.action
        context["action_display"] = self.action_display
        return context


#============================================================================
class TestListInstances(BaseDataTablesDataSource):

    model = models.TestListInstance
    queryset = models.TestListInstance.objects.all
    initial_orderings = ["unit_test_collection__unit__number", "-work_completed"]

    #---------------------------------------------------------------------------
    def set_columns(self):
        self.columns = (
            (self.get_actions, None, None),
            (lambda x: x.unit_test_collection.unit.name, "unit_test_collection__unit__name__exact", "unit_test_collection__unit__number"),
            (lambda x: x.unit_test_collection.frequency.name if x.unit_test_collection.frequency else "Ad-Hoc", "unit_test_collection__frequency", "unit_test_collection__frequency"),
            (lambda x: x.test_list.name, "test_list__name__icontains", "test_list__name"),
            (self.get_work_completed, None, "work_completed"),
            (lambda x: x.created_by.username, "created_by__username__icontains", "created_by__username"),
            (self.get_review_status, None, None),
            (qa_tags.as_pass_fail_status, None, None),
        )

    #----------------------------------------------------------------------
    def get_queryset(self):
        return self.queryset().select_related(
            "test_list__name",
            "testinstance__status",
            "unit_test_collection__unit__name",
            "unit_test_collection__frequency__due_interval",
            "created_by", "modified_by",
        ).prefetch_related("testinstance_set", "testinstance_set__status")

    #----------------------------------------------------------------------
    def get_actions(self, tli):
        template = get_template("qa/testlistinstance_actions.html")
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request": self.request})
        return template.render(c)

    #---------------------------------------------------------------------------
    def get_work_completed(self, tli):
        template = get_template("qa/testlistinstance_work_completed.html")
        c = Context({"instance": tli})
        return template.render(c)

    #----------------------------------------------------------------------
    def get_review_status(self, tli):
        template = get_template("qa/testlistinstance_review_status.html")
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request": self.request})
        return template.render(c)
