from .. import signals #signals import needs to be here so signals get registered

import calendar
import collections
import json
import logging
import math
import os
import shutil
import urllib


from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.template import Context
from django.contrib.auth.context_processors import PermWrapper
from django.template.loader import get_template

from django.views.generic import ListView, UpdateView, View, TemplateView, CreateView
from django.utils.translation import ugettext as _
from django.utils import timezone

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

import numpy
import scipy

from qatrack.contacts.models import Contact
from qatrack.qa import models, utils
from qatrack.qa.views import forms
from qatrack.qa.templatetags import qa_tags
from qatrack.units.models import Unit, UnitType

logger = logging.getLogger('qatrack.console')




#============================================================================
class JSONResponseMixin(object):
    """bare bones JSON response mixin taken from Django docs"""

    def render_to_response(self, context):
        """Returns a JSON response containing 'context' as payload"""
        return self.get_json_response(self.convert_context_to_json(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        """Construct an `HttpResponse` object."""
        return HttpResponse(content, content_type='application/json', **httpresponse_kwargs)

    def convert_context_to_json(self, context):
        """Convert the context dictionary into a JSON object"""
        # Note: This is *EXTREMELY* naive; no checking is done to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)


#============================================================================
class BaseEditTestListInstance(UpdateView):
    model = models.TestListInstance
    context_object_name = "test_list_instance"
    #---------------------------------------------------------------------------

    def get_queryset(self):
        qs = super(BaseEditTestListInstance, self).get_queryset()
        qs = qs.select_related(
            "unit_test_collection",
            "unit_test_collection__unit",
            "test_list",
            "created_by",
            "modified_by",
        )
        return qs

    #----------------------------------------------------------------------
    def add_histories(self, forms):
        """paste historical values onto unit test infos"""

        utc_hist = models.TestListInstance.objects.filter(unit_test_collection=self.object.unit_test_collection, test_list=self.object.test_list).order_by("-work_completed").values_list("work_completed", flat=True)[:settings.NHIST]
        if utc_hist.count() > 0:
            from_date = list(utc_hist)[-1]
        else:
            from_date = timezone.make_aware(timezone.datetime.now() - timezone.timedelta(days=10*self.object.unit_test_collection.frequency.overdue_interval), timezone.get_current_timezone())

        tests = [x.unit_test_info.test for x in self.test_instances]
        histories = utils.tests_history(tests, self.object.unit_test_collection.unit, from_date, test_list=self.object.test_list)
        unit_test_infos = [f.instance.unit_test_info for f in forms]
        unit_test_infos, self.history_dates = utils.add_history_to_utis(unit_test_infos, histories)
        for uti, f in zip(unit_test_infos, forms):
            f.history = uti.history

    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):

        context = super(BaseEditTestListInstance, self).get_context_data(**kwargs)

        # we need to override the default queryset for the formset so that we can pull
        # in all the reference/tolerance data without the ORM generating 100's of queries
        self.test_instances = models.TestInstance.objects.filter(
            test_list_instance=self.object
        ).select_related(
            "reference", "tolerance", "status", "unit_test_info", "unit_test_info__test", "status"
        )

        if self.request.method == "POST":
            formset = self.formset_class(self.request.POST, self.request.FILES, instance=self.get_object(), queryset=self.test_instances, user=self.request.user)
        else:
            formset = self.formset_class(instance=self.get_object(), queryset=self.test_instances, user=self.request.user)

        self.add_histories(formset.forms)
        context["formset"] = formset
        context["history_dates"] = self.history_dates
        context["statuses"] = models.TestInstanceStatus.objects.all()
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
class BaseDataTablesDataSource(ListView):

    model = None
    queryset = None
    initial_orderings = []

    #---------------------------------------------------------------------------
    def render_to_response(self, context):
        if self.kwargs["data"]:
            return HttpResponse(context, content_type='application/json')
        else:
            return super(BaseDataTablesDataSource, self).render_to_response(context)

    #---------------------------------------------------------------------------
    def set_columns(self):
        """must be overridden in child class"""
        self.columns = ()
        raise NotImplementedError

    #----------------------------------------------------------------------
    def set_orderings(self):
        n_orderings = int(self.search_filter_context.get("iSortingCols", 0))

        if n_orderings == 0:
            self.orderings = self.initial_orderings
            return

        order_cols = []
        for x in range(n_orderings):
            col = int(self.search_filter_context.get("iSortCol_%d" % x))
            direction = "" if self.search_filter_context.get("sSortDir_%d" % x, "asc") == "asc" else "-"
            order_cols.append((col, direction))

        self.orderings = []
        for col, direction in order_cols:
            display, search, ordering = self.columns[col]
            if ordering:
                if isinstance(ordering, basestring):
                    self.orderings.append("%s%s" % (direction, ordering))
                else:
                    for o in ordering:
                        self.orderings.append("%s%s" % (direction, o))

    #----------------------------------------------------------------------
    def set_filters(self):
        self.filters = []

        for col, (display, search, ordering) in enumerate(self.columns):

            search_term = self.search_filter_context.get("sSearch_%d" % col)

            if search and search_term:
                if search_term == "null":
                    search_term = None

                if not isinstance(search, basestring):
                    f = None
                    for s, ct in search:
                        q = Q(**{s: search_term, "content_type": ct})
                        if f is None:
                            f = q
                        else:
                            f |= q

                else:
                    f = Q(**{search: search_term})
                self.filters.append(f)

    #----------------------------------------------------------------------
    def set_current_page_objects(self):
        per_page = int(self.search_filter_context.get("iDisplayLength", 100))
        offset = int(self.search_filter_context.get("iDisplayStart", 0))
        self.cur_page_objects = self.filtered_objects[offset:offset+per_page]

    #----------------------------------------------------------------------
    def tabulate_data(self):
        self.table_data = []
        for obj in self.cur_page_objects:
            row = []
            for col, (display, search, ordering) in enumerate(self.columns):
                if callable(display):
                    display = display(obj)
                row.append(display)
            self.table_data.append(row)

    #---------------------------------------------------------------------------
    def get_context_data(self, *args, **kwargs):
        context = super(BaseDataTablesDataSource, self).get_context_data(*args, **kwargs)

        table_data = self.get_table_context_data(context)
        if self.kwargs["data"]:
            return json.dumps(table_data)
        else:
            context.update(table_data)
            return self.get_template_context_data(context)

    #----------------------------------------------------------------------
    def set_search_filter_context(self):
        """create a search and filter context, overridng any cookie values
        with request values"""

        self.search_filter_context = {}

        try:
            for k,v in self.request.COOKIES.items():
                if k.startswith("SpryMedia_DataTables"):
                    break
            else:
                raise KeyError

            cookie_filters = json.loads(urllib.unquote(v))

            for idx, search in enumerate(cookie_filters["aoSearchCols"]):
                for k,v in search.items():
                    self.search_filter_context["%s_%d"%(k,idx)] = v

            self.search_filter_context["iSortingCols"] = 0
            for idx, (col,dir_,_) in enumerate(cookie_filters["aaSorting"]):
                self.search_filter_context["iSortCol_%d" %(idx)] = col
                self.search_filter_context["sSortDir_%d" %(idx)] = dir_
                self.search_filter_context["iSortingCols"] += 1

            self.search_filter_context["iDisplayLength"] = cookie_filters["iLength"]
            self.search_filter_context["iDisplayStart"] = cookie_filters["iStart"]
            self.search_filter_context["iDisplayEnd"] = cookie_filters["iEnd"]

        except KeyError:
            pass

        self.search_filter_context.update(self.request.GET.dict())

    #----------------------------------------------------------------------
    def get_table_context_data(self, base_context):

        all_objects = base_context["object_list"]

        self.set_search_filter_context()

        self.set_columns()
        self.set_orderings()
        self.set_filters()


        self.filtered_objects = all_objects.filter(*self.filters).order_by(*self.orderings)

        self.set_current_page_objects()
        self.tabulate_data()

        context = {
            "data": self.table_data,
            "iTotalRecords": all_objects.count(),
            "iTotalDisplayRecords": self.filtered_objects.count(),
            "sEcho": self.search_filter_context.get("sEcho"),
        }

        return context

    #----------------------------------------------------------------------
    def get_page_title(self):
        return "Generic Data Tables Template View"

    #----------------------------------------------------------------------
    def get_template_context_data(self, context):
        context["page_title"] = self.get_page_title()
        return context


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
        c = Context({"instance": tli, "perms": PermWrapper(self.request.user), "request":self.request})
        return template.render(c)


