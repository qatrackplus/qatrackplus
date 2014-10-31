from .. import signals  # NOQA :signals import needs to be here so signals get registered

import logging
import collections

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse, resolve
from django.template import Context
from django.contrib.auth.context_processors import PermWrapper
from django.template.loader import get_template
from django.utils.translation import ugettext as _

from django.views.generic import UpdateView

from qatrack.qa import models, utils

from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from listable.views import BaseListableView, SELECT

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


class BaseEditTestListInstance(TestListInstanceMixin, UpdateView):
    """A common base for editing existing :model:`qa.TestListInstance`'s"""

    def add_histories(self, forms):
        """paste historical values onto forms"""

        history, history_dates = self.object.history()
        self.history_dates = history_dates
        for f in forms:
            for instance, test_history in history:
                if f.instance == instance:
                    f.history = test_history

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

    def form_valid(self, form):
        """This view should always be subclassed"""
        raise NotImplementedError

    def get_success_url(self):
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        return reverse("unreviewed")


class UTCList(BaseListableView):

    model = models.UnitTestCollection

    action = "perform"
    action_display = "Perform"
    active_only = True
    paginate_by = 50

    fields = (
        "actions",
        "utc_name",
        "due_date",
        "unit__name",
        "frequency__name",
        "assigned_to__name",
        "last_instance_work_completed",
        "last_instance_pass_fail",
        "last_instance_review_status",
    )

    search_fields = {
        "actions": False,
        "utc_name": "utc_name__icontains",
        "assigned_to__name": "assigned_to__name__exact",
        "last_instance_pass_fail": False,
        "last_instance_review_status": False,
    }

    order_fields = {
        "actions": False,
        "frequency__name": "frequency__due_interval",
        "unit__name": "unit__number",
        "last_instance_pass_fail": False,
        "last_instance_review_status": False,
    }

    widgets = {
        "unit__name": SELECT,
        "frequency__name": SELECT,
        "assigned_to__name": SELECT,
    }


    select_related = (
        "last_instance__work_completed",
        "last_instance__created_by",
        "frequency",
        "unit__name",
        "assigned_to__name",
    )

    headers = {
        "utc_name": _("Test List/Cycle"),
        "unit__name": _("Unit"),
        "frequency__name": _("Frequency"),
        "assigned_to__name": _("Assigned To"),
        "last_instance_work_completed": _("Completed"),
        "last_instance_pass_fail": _("Pass/Fail Status"),
        "last_instance_review_status": _("Review Status"),
    }

    prefetch_related  = (
        "last_instance__testinstance_set",
        "last_instance__testinstance_set__status",
        "last_instance__reviewed_by",
        "last_instance__modified_by",
    )

    order_by = ["unit__name", "frequency__name", "utc_name"]

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

    def get_context_data(self, *args, **kwargs):
        context = super(UTCList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url

        return context

    def get_queryset(self):
        """filter queryset for visibility and fetch relevent related objects"""

        qs = super(UTCList, self).get_queryset().filter(
            visible_to__in=self.request.user.groups.all(),
        ).distinct()

        if self.active_only:
            qs = qs.filter(active=True)

        return qs

    def get_extra(self):
        return utils.qs_extra_for_utc_name()

    def frequency__name(self, utc ):
        return utc.frequency.name if utc.frequency else "Ad Hoc"

    def actions(self, utc):
        template = self.templates['actions']
        c = Context({"utc": utc, "request": self.request, "action": self.action})
        return template.render(c)

    def due_date(self, utc):
        template = self.templates['due_date']
        c = Context({"unit_test_collection": utc, "show_icons": settings.ICON_SETTINGS["SHOW_DUE_ICONS"]})
        return template.render(c)

    def last_instance_work_completed(self, utc):
        template = self.templates['work_completed']
        c = Context({"instance": utc.last_instance})
        return template.render(c)

    def last_instance_review_status(self, utc):
        template = self.templates['review_status']
        c = Context({"instance": utc.last_instance, "perms": PermWrapper(self.request.user), "request": self.request})
        c.update(generate_review_status_context(utc.last_instance))
        return template.render(c)

    def last_instance_pass_fail(self, utc):
        template = self.templates['pass_fail']
        c = Context({"instance": utc.last_instance, "exclude": [models.NO_TOL], "show_label": True, "show_icons": settings.ICON_SETTINGS['SHOW_STATUS_ICONS_LISTING']})
        return template.render(c)


class TestListInstances(BaseListableView):
    """
    This view provides a base for any sort of listing of
    :model:`qa.TestListInstance`'s.
    """

    model = models.TestListInstance
    paginate_by = 50

    order_by = ["unit_test_collection__unit__name", "-work_completed"]

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

    widgets = {
        "actions"
        "unit_test_collection__frequency__name": SELECT,
        "unit_test_collection__unit__name": SELECT,
    }

    search_fields = {
        "actions": False,
        "pass_fail": False,
        "review_status": False,
    }


    order_fields = {
        "actions": False,
        "unit_test_collection__unit__name": "unit_test_collection__unit__number",
        "unit_test_collection__frequency__name": "unit_test_collection__frequency__due_interval",
        "review_status": False,
        "pass_fail": False,
    }

    select_related = (
        "test_list__name",
        "testinstance__status",
        "unit_test_collection__unit__name",
        "unit_test_collection__frequency__due_interval",
        "created_by", "modified_by", "reviewed_by",
    )

    prefetch_related = ("testinstance_set", "testinstance_set__status")


    def __init__(self, *args, **kwargs):
        super(TestListInstances, self).__init__(*args, **kwargs)

        self.templates = {
            'actions': get_template("qa/testlistinstance_actions.html"),
            'work_completed': get_template("qa/testlistinstance_work_completed.html"),
            'review_status': get_template("qa/testlistinstance_review_status.html"),
            'pass_fail':  get_template("qa/pass_fail_status.html"),
        }

    def get_page_title(self):
        return "All Test Collections"

    def get_context_data(self, *args, **kwargs):
        context = super(TestListInstances, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url

        context["page_title"] = self.get_page_title()
        return context

    def unit_test_collection__frequency__name(self, tli):
        freq = tli.unit_test_collection.frequency
        return freq.name if freq else "Ad Hoc"

    def actions(self, tli):
        template = self.templates['actions']
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request": self.request})
        return template.render(c)

    def work_completed(self, tli):
        template = self.templates['work_completed']
        c = Context({"instance": tli})
        return template.render(c)

    def review_status(self, tli):
        template = self.templates['review_status']
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request": self.request})
        c.update(generate_review_status_context(tli))
        return template.render(c)

    def pass_fail(self, tli):
        template = self.templates['pass_fail']
        c = Context({"instance": tli, "exclude": [models.NO_TOL], "show_label": True, "show_icons": settings.ICON_SETTINGS['SHOW_STATUS_ICONS_LISTING']})
        return template.render(c)
