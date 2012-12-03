import collections
import json
import calendar
from api import ValueResource
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.http import HttpResponse,HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.template import Context
from django.contrib.auth.context_processors import PermWrapper
from django.template.loader import get_template

from django.views.generic import ListView, UpdateView, View, TemplateView, CreateView, DetailView
from django.utils.translation import ugettext as _
from django.utils import timezone,formats

from qatrack.qa import models,utils
from qatrack.qa.templatetags import qa_tags
from qatrack.units.models import Unit, UnitType
from qatrack.contacts.models import Contact
from qatrack import settings



import logging
logger = logging.getLogger(__name__)

import forms
import math
import os
import textwrap

CONTROL_CHART_AVAILABLE = True
try:
    from qatrack.qa.control_chart import control_chart
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.dates import DateFormatter
    import numpy
except ImportError:
    CONTROL_CHART_AVAILABLE = False

try:
    import numpy
    import scipy
    SCIPY_AVAILABLE = True
except:
    SCIPY_AVAILABLE = False


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

class ChartView(TemplateView):
    """view for creating charts/graphs from data"""
    template_name = "qa/charts.html"

    #----------------------------------------------------------------------
    def create_test_data(self):
        tlc_content_type = ContentType.objects.get_for_model(models.TestListCycle).pk

        utcs = models.UnitTestCollection.objects.all().values(
            "frequency",
            "content_type",
            "testlist",
            "testlistcycle",
            "unit",
            "testlistcycle__test_lists"
        )

        self.unit_frequencies = collections.defaultdict(lambda:collections.defaultdict(list))

        for utc in utcs:
            unit = utc["unit"]#.unit.pk
            freq = utc["frequency"]#.pk
            if utc["content_type"] == tlc_content_type:
                test_list = utc["testlistcycle__test_lists"]
            else:
                test_list = utc["testlist"]

            self.unit_frequencies[unit][freq].append(test_list)

        #uniquify unit/freq lists
        for utc in utcs:
            unit = utc["unit"]
            freq = utc["frequency"]
            self.unit_frequencies[unit][freq] = list(sorted(set(self.unit_frequencies[unit][freq])))

        self.test_data = {
            "test_lists":{},
            "unit_frequency_lists":self.unit_frequencies,
        }


        for test_list in self.test_lists:

            tests = [x.pk for x in test_list.tests.all()]
            if test_list.sublists:
                for sublist in test_list.sublists.all():
                    tests.extend(list(sublist.tests.values_list("pk",flat=True)))

            self.test_data["test_lists"][test_list.pk] = tests


        return json.dumps(self.test_data)

    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):
        """add default dates to context"""
        context = super(ChartView,self).get_context_data(**kwargs)

        self.set_test_lists()
        self.set_tests()

        test_data = self.create_test_data()

        c = {
            "cc_available":CONTROL_CHART_AVAILABLE,
            "from_date": timezone.now().date()-timezone.timedelta(days=180),
            "to_date":timezone.now().date()+timezone.timedelta(days=1),
            "frequencies":models.Frequency.objects.all(),
            "tests":self.tests,
            "test_lists":self.test_lists,
            "categories":models.Category.objects.all(),
            "statuses":models.TestInstanceStatus.objects.all(),
            "units":Unit.objects.all().select_related("type"),
            "test_data": test_data,
            "chart_data_url":reverse("chart_data"),
            "control_chart_url":reverse("control_chart"),

        }
        context.update(c)
        return context
    #----------------------------------------------------------------------
    def set_tests(self):
        self.tests = models.Test.objects.order_by("name").values(
            "pk",
            "category",
            "name",
            "description",
        )
    #---------------------------------------------------------------------------
    def set_test_lists(self):
        self.test_lists = models.TestList.objects.order_by("name").prefetch_related(
            "sublists",
            "tests",
        )



class BaseChartView(View):
    ISO_FORMAT = False
    #----------------------------------------------------------------------
    def get(self,request):

        data = self.get_plot_data()
        table = self.create_data_table()
        resp = self.render_to_response({"data":data,"table":table})

        return resp

    #----------------------------------------------------------------------
    def create_data_table(self):

        utis = list(set([x.unit_test_info for x in self.tis]))

        headers = []
        max_len = 0
        cols = []
        for uti in utis:
            headers.append("%s %s" %(uti.unit.name,uti.test.name))
            col = [(ti.work_completed,ti.value_display()) for ti in self.tis if ti.unit_test_info == uti]
            cols.append(col)
            max_len = max(len(col),max_len)

        rows = []
        for idx in range(max_len):
            row = []
            for col in cols:
                try:
                    row.append(col[idx])
                except IndexError:
                    row.append(["",""])
                    pass
            rows.append(row)


        context = Context({
            "rows":rows,
            "headers":headers
        })
        template = get_template("qa/qa_data_table.html")

        return template.render(context)
    #----------------------------------------------------------------------
    def get_date(self,key,default):
        try:
            d = timezone.datetime.strptime(self.request.GET.get(key),settings.SIMPLE_DATE_FORMAT)
        except:
            d = default

        if timezone.is_naive(d):
            d = timezone.make_aware(d,timezone.get_current_timezone())

        return d

    #---------------------------------------------------------------------------
    def convert_date(self,dt):
        return dt.isoformat()
    #----------------------------------------------------------------------
    def get_plot_data(self):

        tests = self.request.GET.getlist("tests[]",[])
        units = self.request.GET.getlist("units[]",[])
        statuses = self.request.GET.getlist("statuses[]",models.TestInstanceStatus.objects.values_list("pk",flat=True))

        now = timezone.datetime.now()
        from_date = self.get_date("from_date",now-timezone.timedelta(days=180))
        to_date = self.get_date("to_date",now)

        self.tis = models.TestInstance.objects.filter(
            unit_test_info__test__pk__in=tests,
            unit_test_info__unit__pk__in=units,
            status__pk__in = statuses,
            work_completed__gte = from_date,
            work_completed__lte = to_date,
        ).select_related(
            "reference","tolerance","status","unit_test_info","unit_test_info__test","unit_test_info__unit","status"
        ).order_by(
            "work_completed"
        )


        vals_dict = lambda : {"data":[],"values":[],"dates":[],"references":[],"act_low":[],"tol_low":[],"tol_high":[],"act_high":[]}
        data = collections.defaultdict(vals_dict)

        for ti in self.tis:
            uti = ti.unit_test_info
            d = timezone.make_naive(ti.work_completed,timezone.get_current_timezone())
            d = self.convert_date(d)
            data[uti.pk]["data"].append([d,ti.value])
            data[uti.pk]["values"].append(ti.value)


            if ti.reference is not None:
                data[uti.pk]["references"].append(ti.reference.value)
            else:
                data[uti.pk]["references"].append(None)

            if ti.tolerance is not None and ti.reference is not None:
                tols = ti.tolerance.tolerances_for_value(ti.reference.value)
            else:
                tols = {"act_high":None,"act_low":None,"tol_low":None,"tol_high":None}
            for k,v in tols.items():
                data[uti.pk][k].append(v)

            data[uti.pk]["dates"].append(d)
            data[uti.pk]["unit"] = {"name":uti.unit.name,"pk":uti.unit.pk}
            data[uti.pk]["test"] = {"name":uti.test.name,"pk":uti.test.pk}


        return data

#============================================================================
class BasicChartData(JSONResponseMixin,BaseChartView):
    pass


#============================================================================
class ControlChartImage(BaseChartView):
    """Return a control chart image from given qa data"""

    #---------------------------------------------------------------------------
    def convert_date(self,dt):
        return dt

    #----------------------------------------------------------------------
    def get_number_from_request(self,param,default,dtype=float):
        try:
            v = dtype(self.request.GET.get(param,default))
        except:
            v = default
        return v
    #----------------------------------------------------------------------
    def render_to_response(self,context):
        if not CONTROL_CHART_AVAILABLE:
            raise Http404


        fig=Figure(dpi=72,facecolor="white")
        dpi = fig.get_dpi()
        fig.set_size_inches(
            self.get_number_from_request("width",700)/dpi,
            self.get_number_from_request("height",480)/dpi,
        )
        canvas=FigureCanvas(fig)

        dates,data = [],[]

        if context["data"] and context["data"].values():

            for d,v in context["data"].values()[0]["data"]:
                if None not in (d,v):
                    dates.append(d)
                    data.append(v)

        n_baseline_subgroups = self.get_number_from_request("n_baseline_subgroups",2,dtype=int)
        n_baseline_subgroups = max(2,n_baseline_subgroups)

        subgroup_size = self.get_number_from_request("subgroup_size",2,dtype=int)
        if subgroup_size <1 or subgroup_size >100:
            subgroup_size = 1

        if self.request.GET.get("fit_data","") == "true":
            include_fit = True
        else:
            include_fit = False


        response = HttpResponse(mimetype="image/png")
        if n_baseline_subgroups < 1 or n_baseline_subgroups > len(data)/subgroup_size:
            fig.text(0.1,0.9,"Not enough data for control chart", fontsize=20)
            canvas.print_png(response)
        else:
            try:
                control_chart.display(fig, numpy.array(data), subgroup_size, n_baseline_subgroups, fit = include_fit,dates=dates)
                fig.autofmt_xdate()

                canvas.print_png(response)

            except (RuntimeError,OverflowError) as e:
                fig.clf()
                msg = "There was a problem generating your control chart:\n"
                msg += e.message
                fig.text(0.1,0.9,"\n".join(textwrap.wrap(msg,40)) , fontsize=12)
                canvas.print_png(response)

        return response

#============================================================================
class CompositeCalculation(JSONResponseMixin, View):
    """validate all qa tests in the request for the :model:`TestList` with id test_list_id"""

    #----------------------------------------------------------------------
    def get_json_data(self,name):
        """return python data from GET json data"""
        json_string = self.request.POST.get(name)
        if not json_string:
            return

        try:
            return json.loads(json_string)
        except (KeyError, ValueError):
            return

    #----------------------------------------------------------------------
    def post(self,*args, **kwargs):
        """calculate and return all composite values"""

        self.set_composite_test_data()
        if not self.composite_tests:
            return self.render_to_response({"success":False,"errors":["No Valid Composite ID's"]})

        self.set_calculation_context()
        if not self.calculation_context:
            return self.render_to_response({"success":False,"errors":["Invalid QA Values"]})

        self.set_dependencies()
        self.resolve_dependency_order()

        results = {}

        for slug in self.cyclic_tests:
            results[slug] = {'value':None, 'error':"Cyclic test dependency"}

        for slug in self.calculation_order:
            raw_procedure = self.composite_tests[slug]
            procedure = self.process_procedure(raw_procedure)
            try:
                code = compile(procedure,"<string>","exec")
                exec code in self.calculation_context
                result = self.calculation_context["result"]
                results[slug] = { 'value': result,'error':None }
                self.calculation_context[slug]=result
            except Exception as e:
                results[slug] = {'value':None, 'error':"Invalid Test"}
            finally:
                if "result" in self.calculation_context:
                    del self.calculation_context["result"]

        return self.render_to_response({"success":True,"errors":[],"results":results})
    #----------------------------------------------------------------------
    def set_composite_test_data(self):
        composite_ids = self.get_json_data("composite_ids")

        if composite_ids is None:
            self.composite_tests = {}
            return


        composite_tests = models.Test.objects.filter(
            pk__in=composite_ids.values()
        ).values_list("slug","calculation_procedure")

        self.composite_tests = dict(composite_tests)

    #---------------------------------------------------------------------------
    def process_procedure(self,procedure):
        """prepare raw procedure for evaluation"""
        return "\n".join(["from __future__ import division",procedure,"\n"]).replace('\r','\n')
    #----------------------------------------------------------------------
    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""
        values = self.get_json_data("qavalues")
        if values is None:
            self.calculation_context = {}
            return

        self.calculation_context = {
            "math":math,
        }

        if SCIPY_AVAILABLE:
            self.calculation_context["scipy"] = scipy
            self.calculation_context["numpy"] = numpy

        for slug,info in values.iteritems():
            val = info["current_value"]
            if slug not in self.composite_tests:
                try:
                    self.calculation_context[slug] = float(val)
                except (ValueError, TypeError):
                    self.calculation_context[slug] = val

    #----------------------------------------------------------------------
    def set_dependencies(self):
        """figure out composite dependencies of composite tests"""

        self.dependencies = {}
        slugs = self.composite_tests.keys()
        for slug  in slugs:
            tokens = utils.tokenize_composite_calc(self.composite_tests[slug])
            dependencies = [s for s in slugs if s in tokens and s != slug]
            self.dependencies[slug] = set(dependencies)

    #----------------------------------------------------------------------
    def resolve_dependency_order(self):
        """resolve calculation order dependencies using topological sort"""
        #see http://code.activestate.com/recipes/577413-topological-sort/
        data = dict(self.dependencies)
        for k, v in data.items():
            v.discard(k) # Ignore self dependencies
        extra_items_in_deps = reduce(set.union, data.values()) - set(data.keys())
        data.update(dict((item,set()) for item in extra_items_in_deps))
        deps = []
        while True:
            ordered = set(item for item,dep in data.items() if not dep)
            if not ordered:
                break
            deps.extend(list(sorted(ordered)))
            data = dict((item, (dep - ordered)) for item,dep in data.items() if item not in ordered)

        self.calculation_order = deps
        self.cyclic_tests = data.keys()



#====================================================================================
class ChooseUnit(ListView):
    """choose a unit to perform qa on for this session"""
    model = UnitType
    context_object_name = "unit_types"

    #---------------------------------------------------------------------------
    def get_queryset(self):
        return UnitType.objects.all().order_by("unit__number").prefetch_related("unit_set")
    #----------------------------------------------------------------------
    def get_context_data(self,*args,**kwargs):
        """reorder unit types"""
        context = super(ChooseUnit,self).get_context_data(*args,**kwargs)
        uts = [ut for ut in context["unit_types"] if len(ut.unit_set.all()) >0]
        context["unit_types"] = utils.unique(uts)
        return context



#============================================================================
class PerformQA(CreateView):
    """view for users to complete a qa test list"""

    form_class = forms.CreateTestListInstanceForm
    model = models.TestListInstance

    #----------------------------------------------------------------------
    def set_test_lists(self,current_day):

        self.test_list = self.unit_test_col.get_list(current_day)
        if self.test_list is None:
            raise Http404

        self.all_lists = [self.test_list]+list(self.test_list.sublists.all())
    #----------------------------------------------------------------------
    def set_all_tests(self):
        self.all_tests = []
        for test_list in self.all_lists:
            tests = test_list.tests.all().order_by("testlistmembership__order")
            self.all_tests.extend(tests)
    #----------------------------------------------------------------------
    def set_unit_test_collection(self):
        self.unit_test_col = get_object_or_404(
            models.UnitTestCollection.objects.select_related(
                "unit","frequency","last_instance"
            ).filter(
                active=True,
                visible_to__in = self.request.user.groups.all(),
            ).distinct(),
            pk=self.kwargs["pk"]
        )
    #----------------------------------------------------------------------
    def set_actual_day(self):
        cycle_membership = models.TestListCycleMembership.objects.filter(
            test_list = self.test_list,
            cycle = self.unit_test_col.tests_object
        )

        self.actual_day = 0
        self.is_cycle = False
        if cycle_membership:
            self.is_cycle = True
            self.actual_day = cycle_membership[0].order
    #----------------------------------------------------------------------
    def set_last_day(self):


        self.last_day = None

        if self.unit_test_col.last_instance:
            last_membership = models.TestListCycleMembership.objects.filter(
                test_list = self.unit_test_col.last_instance.test_list,
                cycle = self.unit_test_col.tests_object
            )
            if last_membership:
                self.last_day = last_membership[0].order + 1

    #----------------------------------------------------------------------
    def set_unit_test_infos(self):
        utis = models.UnitTestInfo.objects.filter(
            unit = self.unit_test_col.unit,
            test__in = self.all_tests,
            active=True,
        ).select_related(
            "reference",
            "test__category",
            "test__pk",
            "tolerance",
            "unit",
        )

        #make sure utis are correctly ordered
        uti_tests = [x.test for x in utis]
        self.unit_test_infos = []
        for test in self.all_tests:
            try:
                self.unit_test_infos.append(utis[uti_tests.index(test)])
            except ValueError:
                msg =  "Do not treat! Please call physics.  Test '%s' is missing information for this unit "% test.name
                logger.error(msg+ " Test=%d"%test.pk)
                messages.error(self.request,_(msg))

    #----------------------------------------------------------------------
    def add_histories(self):
        """paste historical values onto unit test infos"""
        from_date = timezone.make_aware(timezone.datetime.now() - timezone.timedelta(days=10*self.unit_test_col.frequency.overdue_interval),timezone.get_current_timezone())
        histories = utils.tests_history(self.all_tests,self.unit_test_col.unit,from_date,test_list=self.test_list)
        self.unit_test_infos, self.history_dates = utils.add_history_to_utis(self.unit_test_infos,histories)

    #----------------------------------------------------------------------
    def form_valid(self,form):

        context = self.get_context_data()
        formset = context["formset"]

        for ti_form in formset:
            ti_form.in_progress = form.instance.in_progress

        if formset.is_valid():

            self.object = form.save(commit=False)
            self.object.test_list = self.test_list
            self.object.unit_test_collection = self.unit_test_col
            self.object.created_by = self.request.user
            self.object.modified_by= self.request.user

            if self.object.work_completed is None:
                self.object.work_completed = timezone.make_aware(timezone.datetime.now(),timezone=timezone.get_current_timezone())

            self.object.save()

            status=models.TestInstanceStatus.objects.default()
            if form.fields.has_key("status"):
                val = form["status"].value()
                if val not in ("", None):
                    status = models.TestInstanceStatus.objects.get(pk=val)

            for ti_form in formset:
                ti = models.TestInstance(
                    value=ti_form.cleaned_data.get("value",None),
                    skipped=ti_form.cleaned_data.get("skipped",False),
                    comment=ti_form.cleaned_data.get("comment",""),
                    unit_test_info = ti_form.unit_test_info,
                    reference = ti_form.unit_test_info.reference,
                    tolerance = ti_form.unit_test_info.tolerance,
                    status = status,
                    created_by = self.request.user,
                    modified_by = self.request.user,
                    in_progress = self.object.in_progress,
                    test_list_instance=self.object,
                    work_started=self.object.work_started,
                    work_completed=self.object.work_completed,
                )
                try:
                    ti.save()
                except ZeroDivisionError:

                    msga = "Tried to calculate percent diff with a zero reference value. "

                    ti.skipped = True
                    ti.comment = msga + " Original value was %s" % ti.value
                    ti.value = None
                    ti.save()

                    logger.error(msga+ " UTI=%d"%ti.unit_test_info.pk)
                    msg =  "Please call physics.  Test %s is configured incorrectly on this unit. "% ti.unit_test_info.test.name
                    msg += msga
                    messages.error(self.request,_(msg))

            #let user know request succeeded and return to unit list
            messages.success(self.request,_("Successfully submitted %s "% self.object.test_list.name))

            return HttpResponseRedirect(self.get_success_url())
        else:
            context["form"] = form
            return self.render_to_response(context)

    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):

        context = super(PerformQA,self).get_context_data(**kwargs)

        #explicity refresh session expiry to prevent situation where a session
        #expires in between the time a user requests a page and then submits the page
        #causing them to lose all the data they entered
        self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        if models.TestInstanceStatus.objects.default() is None:
            messages.error(
                self.request,"There must be at least one Test Status defined before performing a TestList"
            )
            return context

        self.set_unit_test_collection()
        self.set_test_lists(self.get_requested_day_to_perform())
        self.set_actual_day()
        self.set_last_day()
        self.set_all_tests()
        self.set_unit_test_infos()
        self.add_histories()

        if self.request.method == "POST":
            formset = forms.CreateTestInstanceFormSet(self.request.POST,self.request.FILES,unit_test_infos=self.unit_test_infos)
        else:
            formset = forms.CreateTestInstanceFormSet(unit_test_infos=self.unit_test_infos)


        context["formset"] = formset

        context["history_dates"] = self.history_dates
        context['categories'] = set([x.test.category for x in self.unit_test_infos])
        context['current_day'] = self.actual_day+1
        context["last_instance"] = self.unit_test_col.last_instance
        context['last_day'] = self.last_day
        ndays = len(self.unit_test_col.tests_object)
        if ndays > 1:
            context['days'] = range(1,ndays+1)

        context["test_list"] = self.test_list
        context["unit_test_collection"] = self.unit_test_col
        context["contacts"] = list(Contact.objects.all().order_by("name"))
        return context

    #----------------------------------------------------------------------
    def get_requested_day_to_perform(self):
        """request comes in as 1 based day, convert to zero based"""
        try:
            day = int(self.request.GET.get("day"))-1
        except (ValueError,TypeError,KeyError):
            day = None
        return day
    #----------------------------------------------------------------------
    def get_success_url(self):
        next_ = self.request.GET.get("next",None)
        if next_ is not None:
            return next_

        kwargs = {
            "unit_number":self.unit_test_col.unit.number,
            "frequency":self.unit_test_col.frequency.slug
        }

        if not self.request.user.has_perm("qa.can_choose_frequency"):
            kwargs["frequency"] = "short-interval"

        return reverse("qa_by_frequency_unit",kwargs=kwargs)


#============================================================================
class BaseEditTestListInstance(UpdateView):
    model = models.TestListInstance
    context_object_name = "test_list_instance"
    #---------------------------------------------------------------------------
    def get_queryset(self):
        qs = super(BaseEditTestListInstance,self).get_queryset()
        qs = qs.select_related(
            "unit_test_collection",
            "unit_test_collection__unit",
            "test_list",
            "created_by",
            "modified_by",
        )
        return qs

    #----------------------------------------------------------------------
    def add_histories(self,forms):
        """paste historical values onto unit test infos"""
        from_date = timezone.make_aware(timezone.datetime.now() - timezone.timedelta(days=10*self.object.unit_test_collection.frequency.overdue_interval),timezone.get_current_timezone())
        tests = [x.unit_test_info.test for x in self.test_instances]
        histories = utils.tests_history(tests,self.object.unit_test_collection.unit,from_date,test_list=self.object.test_list)
        unit_test_infos = [f.instance.unit_test_info for f in forms]
        unit_test_infos, self.history_dates = utils.add_history_to_utis(unit_test_infos,histories)
        for uti,f in zip(unit_test_infos,forms):
            f.history = uti.history


    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):

        context = super(BaseEditTestListInstance,self).get_context_data(**kwargs)

        #we need to override the default queryset for the formset so that we can pull
        #in all the reference/tolerance data without the ORM generating 100's of queries
        self.test_instances = models.TestInstance.objects.filter(
            test_list_instance=self.object
        ).select_related(
            "reference","tolerance","status","unit_test_info","unit_test_info__test","status"
        )

        if self.request.method == "POST":
            formset = self.formset_class(self.request.POST,self.request.FILES,instance=self.get_object(),queryset=self.test_instances)
        else:
            formset = self.formset_class(instance=self.get_object(),queryset=self.test_instances)

        self.add_histories(formset.forms)
        context["formset"] = formset
        context["history_dates"] = self.history_dates
        context["statuses"] = models.TestInstanceStatus.objects.all()
        return context

    #----------------------------------------------------------------------
    def form_valid(self,form):
        raise NotImplementedError
    #----------------------------------------------------------------------
    def get_success_url(self):
        next_ = self.request.GET.get("next",None)
        if next_ is not None:
            return next_

        return reverse("unreviewed")


#============================================================================
class ReviewTestListInstance(BaseEditTestListInstance):
    form_class = forms.ReviewTestListInstanceForm
    formset_class = forms.ReviewTestInstanceFormSet
    template_name_suffix = "_review"

    #----------------------------------------------------------------------
    def form_valid(self,form):
        context = self.get_context_data()
        formset = context["formset"]

        update_time = timezone.make_aware(timezone.datetime.now(),timezone.get_current_timezone())
        update_user = self.request.user

        test_list_instance = form.save(commit=False)
        test_list_instance.modified = update_time
        test_list_instance.modified_by = update_user
        test_list_instance.save()

        # note we are not calling if formset.is_valid() here since we assume
        # validity given we are only changing the status of the test_instances.
        # Also, we are not cleaning the data since a 500 will be raised if
        # something other than a valid int is passed for the status.
        #
        # If you add something here be very careful to check that the data
        # is clean before updating the db

        #for efficiency update statuses in bulk rather than test by test basis
        status_groups = collections.defaultdict(list)
        for ti_form in formset:
            status_pk = int(ti_form["status"].value())
            status_groups[status_pk].append(ti_form.instance.pk)

        for status_pk,test_instance_pks in status_groups.items():
            status = models.TestInstanceStatus.objects.get(pk=status_pk)
            models.TestInstance.objects.filter(pk__in=test_instance_pks).update(
                status=status,
                modified_by=update_user,
                modified = update_time
            )

        #let user know request succeeded and return to unit list
        messages.success(self.request,_("Successfully updated %s "% self.object.test_list.name))
        return HttpResponseRedirect(self.get_success_url())

#============================================================================
class EditTestListInstance(BaseEditTestListInstance):
    """view for users to complete a qa test list"""

    form_class = forms.UpdateTestListInstanceForm
    formset_class = forms.UpdateTestInstanceFormSet

    #----------------------------------------------------------------------
    def form_valid(self,form):
        context = self.get_context_data()
        formset = context["formset"]

        for ti_form in formset:
            ti_form.in_progress = form.instance.in_progress

        if formset.is_valid():

            self.object = form.save(commit=False)
            self.update_test_list_instance()

            status_pk = None
            if form.fields.has_key("status"):
                status_pk = form["status"].value()
            status= self.get_status_object(status_pk)

            for ti_form in formset:
                ti = ti_form.save(commit=False)
                self.update_test_instance(ti,status)

            #let user know request succeeded and return to unit list
            messages.success(self.request,_("Successfully submitted %s "% self.object.test_list.name))

            return HttpResponseRedirect(self.get_success_url())
        else:
            context["form"] = form
            return self.render_to_response(context)

    #----------------------------------------------------------------------
    def update_test_list_instance(self):
        self.object.created_by = self.request.user
        self.object.modified_by= self.request.user

        if self.object.work_completed is None:
            self.object.work_completed = timezone.make_aware(timezone.datetime.now(),timezone=timezone.get_current_timezone())

        self.object.save()
    #----------------------------------------------------------------------
    def get_status_object(self,status_pk):
        try:
            status = models.TestInstanceStatus.objects.get(pk=status_pk)
        except (models.TestInstanceStatus.DoesNotExist,ValueError):
            status = models.TestInstanceStatus.objects.default()
        return status
    #----------------------------------------------------------------------
    def update_test_instance(self,test_instance,status):
        ti = test_instance
        ti.status = status
        ti.created_by = self.request.user
        ti.modified_by = self.request.user
        ti.in_progress = self.object.in_progress
        ti.work_started=self.object.work_started
        ti.work_completed=self.object.work_completed

        try:
            ti.save()
        except ZeroDivisionError:

            msga = "Tried to calculate percent diff with a zero reference value. "

            ti.skipped = True
            ti.comment = msga + " Original value was %s" % ti.value
            ti.value = None
            ti.save()

            logger.error(msga+ " UTI=%d"%ti.unit_test_info.pk)
            msg =  "Please call physics.  Test %s is configured incorrectly on this unit. "% ti.unit_test_info.test.name
            msg += msga
            messages.error(self.request,_(msg))



#============================================================================
class BaseDataTablesDataSource(ListView):

    model = None
    queryset = None

    def render_to_response(self, context):
        if self.kwargs["data"]:
            return HttpResponse(context, content_type='application/json')
        else:
            return super(BaseDataTablesDataSource,self).render_to_response(context)
    #---------------------------------------------------------------------------
    def set_columns(self):
        """must be overridden in child class"""
        self.columns = ()
    #----------------------------------------------------------------------
    def set_orderings(self):
        n_orderings = int(self.request.GET.get("iSortingCols",0))
        order_cols = {}
        for x in range(n_orderings):
            col = int(self.request.GET.get("iSortCol_%d"%x))
            order_cols[col] = "" if self.request.GET.get("sSortDir_%d"%x) == "asc" else "-"

        self.orderings = []
        for col, (display, search, ordering) in enumerate(self.columns):
            if (col in order_cols) and ordering:
                if isinstance(ordering,basestring):
                    self.orderings.append("%s%s" % (order_cols[col],ordering))
                else:
                    for o in ordering:
                        self.orderings.append("%s%s" % (order_cols[col],o))


    #----------------------------------------------------------------------
    def set_filters(self):
        self.filters = []
        for col, (display, search, ordering) in enumerate(self.columns):

            search_term = self.request.GET.get("sSearch_%d"%col)
            if search and search_term:
                if not isinstance(search,basestring):
                    f = None
                    for s,ct in search:
                        q = Q(**{s:search_term,"content_type":ct})
                        if f is None:
                            f = q
                        else:
                            f |= q

                else:
                    f = Q(**{search:search_term})
                self.filters.append(f)

    #----------------------------------------------------------------------
    def set_current_page_objects(self):
        per_page = int(self.request.GET.get("iDisplayLength"))
        offset = int(self.request.GET.get("iDisplayStart"))
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
    def get_context_data(self,*args,**kwargs):
        context = super(BaseDataTablesDataSource,self).get_context_data(*args,**kwargs)
        if self.kwargs["data"]:
            return self.get_table_context_data(context)
        else:
            return self.get_template_context_data(context)
    #----------------------------------------------------------------------
    def get_table_context_data(self,base_context):

        all_objects = base_context["object_list"]

        self.set_columns()
        self.set_filters()
        self.set_orderings()

        self.filtered_objects =  all_objects.filter(*self.filters).order_by(*self.orderings)

        self.set_current_page_objects()
        self.tabulate_data()

        context = {
            "data":self.table_data,
            "iTotalRecords":all_objects.count(),
            "iTotalDisplayRecords":self.filtered_objects.count(),
            "sEcho":self.request.GET.get("sEcho"),
        }

        return json.dumps(context)

    #----------------------------------------------------------------------
    def get_data_source(self):
        raise NotImplementedError
    #----------------------------------------------------------------------
    def get_page_title(self):
        return "Generic Data Tables Template View"
    #----------------------------------------------------------------------
    def get_template_context_data(self,context):
        context["page_title"] = self.get_page_title()
        return context



#============================================================================
class UTCList(BaseDataTablesDataSource):
    model = models.UnitTestCollection
    action = "perform"
    action_display = "Perform"


    #---------------------------------------------------------------------------
    def set_columns(self):
        self.columns = (
            (self.get_actions,None,None),
            (
                lambda x:x.tests_object.name, (
                    ("testlist__name__icontains",ContentType.objects.get_for_model(models.TestList)),
                    ("testlistcycle__name__icontains",ContentType.objects.get_for_model(models.TestListCycle))
                ),
                ("testlist__name","testlistcycle__name",)
            ),
            (qa_tags.as_due_date, None,None),
            (lambda x:x.unit.name, "unit__name__exact", "unit__number"),
            (lambda x:x.frequency.name, "frequency__name__exact", "frequency__due_interval"),

            (lambda x:x.assigned_to.name,"assigned_to__name__contains","assigned_to__name"),
            (self.get_last_instance_work_completed,None,"last_instance__work_completed"),
            (self.get_last_instance_pass_fail,None,None),
            (self.get_last_instance_review_status,None,None),
        )

    #----------------------------------------------------------------------
    def get_actions(self,utc):
        template = get_template("qa/unittestcollection_actions.html")
        c = Context({"utc":utc,"request":self.request,"action":self.action})
        return template.render(c)

    #---------------------------------------------------------------------------
    def get_last_instance_work_completed(self,utc):
        template = get_template("qa/testlistinstance_work_completed.html")
        c = Context({"instance":utc.last_instance})
        return template.render(c)
    #----------------------------------------------------------------------
    def get_last_instance_review_status(self,utc):
        template = get_template("qa/testlistinstance_review_status.html")
        c = Context({"instance":utc.last_instance,"perms":PermWrapper(self.request.user),"request":self.request})
        return template.render(c)

    #----------------------------------------------------------------------
    def get_last_instance_pass_fail(self,utc):
        return qa_tags.as_pass_fail_status(utc.last_instance)
    #----------------------------------------------------------------------
    def get_queryset(self):

        qs = super(UTCList,self).get_queryset().filter(
            active=True,
            visible_to__in = self.request.user.groups.all(),
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
        )#.order_by("unit__number","testlist__name","testlistcycle__name",)

        return qs.distinct()

    #----------------------------------------------------------------------
    def get_page_title(self):
        return "All Test Collections"

    #----------------------------------------------------------------------
    def get_template_context_data(self,context):
        #context = super(UTCList,self).get_context_data(*args,**kwargs)
        context["page_title"] = self.get_page_title()
        context["action"] = self.action
        context["action_display"] = self.action_display
        return context

#====================================================================================
class UTCReview(UTCList):
    action = "review"
    action_display = "Review"
    #---------------------------------------------------------------------------
    def get_page_title(self):
        return "Review Test List Data"

#====================================================================================
class UTCFrequencyReview(UTCReview):

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""

        qs = super(UTCFrequencyReview,self).get_queryset()

        freq = self.kwargs["frequency"]
        if freq == "short-interval":
            self.frequencies = models.Frequency.objects.filter(due_interval__lte=14)
        else:
            self.frequencies = models.Frequency.objects.filter(slug__in=self.kwargs["frequency"].split("/"))

        return qs.filter(
            frequency__slug__in=self.frequencies.values_list("slug",flat=True),
        ).distinct()

    #---------------------------------------------------------------------------
    def get_page_title(self):
        return " Review " + ", ".join([x.name for x in self.frequencies]) + " Test Lists"


#====================================================================================
class UTCUnitReview(UTCReview):

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""
        qs = super(UTCUnitReview,self).get_queryset()
        self.units = Unit.objects.filter(number__in=self.kwargs["unit_number"].split("/"))
        return qs.filter(unit__in=self.units).order_by("unit__number")

    #---------------------------------------------------------------------------
    def get_page_title(self):
        return "Review " + ", ".join([x.name for x in self.units]) + " Test Lists"

#====================================================================================
class ChooseUnitForReview(ChooseUnit):
    template_name_suffix = "_choose_for_review"

#====================================================================================
class ChooseFrequencyForReview(ListView):

    model = models.Frequency
    context_object_name = "frequencies"
    template_name_suffix = "_choose_for_review"

#============================================================================
class FrequencyList(UTCList):
    """list daily/monthly/annual test lists for a unit"""

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""

        qs = super(FrequencyList,self).get_queryset()

        freqs = self.kwargs["frequency"].split("/")
        self.frequencies = list(models.Frequency.objects.filter(slug__in=freqs))

        if "short-interval" in freqs:
            self.frequencies.extend(list(models.Frequency.objects.filter(due_interval__lte=14)))

        return qs.filter(
            frequency__in=self.frequencies,
        ).distinct()
    #----------------------------------------------------------------------
    def get_page_title(self):
        return ",".join([x.name for x in self.frequencies]) + " Test Lists"
#============================================================================
class UnitFrequencyList(FrequencyList):
    """list daily/monthly/annual test lists for a unit"""

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""
        qs = super(UnitFrequencyList,self).get_queryset()
        self.units = Unit.objects.filter(number__in=self.kwargs["unit_number"].split("/"))
        return qs.filter(unit__in=self.units)
    #----------------------------------------------------------------------
    def get_page_title(self):
        title = ", ".join([x.name for x in self.units])
        title+= " " + ", ".join([x.name for x in self.frequencies]) + " Test Lists"
        return  title


#====================================================================================
class UnitList(UTCList):
    """list qa filtered by unit"""

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""
        qs = super(UnitList,self).get_queryset()
        self.units = Unit.objects.filter(
            number__in=self.kwargs["unit_number"].split("/")
        )
        return qs.filter(unit__in=self.units)

    #----------------------------------------------------------------------
    def get_page_title(self):
        title = ", ".join([x.name for x in self.units]) + " Test Lists"
        return  title




#============================================================================
class TestListInstances(BaseDataTablesDataSource):

    model = models.TestListInstance
    queryset = models.TestListInstance.objects.all

    #---------------------------------------------------------------------------
    def set_columns(self):
        self.columns = (
            (self.get_actions,None,None),
            (lambda x:x.unit_test_collection.unit.name, "unit_test_collection__unit__name__exact", "unit_test_collection__unit__number"),
            (lambda x:x.unit_test_collection.frequency.name, "unit_test_collection__frequency__name__exact", "unit_test_collection__frequency__name"),
            (lambda x:x.test_list.name,"test_list__name__contains","test_list__name"),
            (self.get_work_completed,None,"work_completed"),
            (lambda x:x.created_by.username,"created_by__username__contains","created_by__username"),
            (self.get_review_status,None,None),
            (qa_tags.as_pass_fail_status,None,None),
        )

    #----------------------------------------------------------------------
    def get_queryset(self):
        return self.queryset().select_related(
            "test_list__name",
            "testinstance__status",
            "unit_test_collection__unit__name",
            "unit_test_collection__frequency__due_interval",
            "created_by","modified_by",
        ).prefetch_related("testinstance_set","testinstance_set__status")

    #----------------------------------------------------------------------
    def get_actions(self,tli):
        template = get_template("qa/testlistinstance_actions.html")
        c = Context({"instance":tli,"perms":PermWrapper(self.request.user),"request":self.request})
        return template.render(c)

    #---------------------------------------------------------------------------
    def get_work_completed(self,tli):
        template = get_template("qa/testlistinstance_work_completed.html")
        c = Context({"instance":tli})
        return template.render(c)
    #----------------------------------------------------------------------
    def get_review_status(self,tli):
        template = get_template("qa/testlistinstance_review_status.html")
        c = Context({"instance":tli,"perms":PermWrapper(self.request.user)})
        return template.render(c)



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
        qs = super(UTCInstances,self).get_queryset()
        return qs.filter(unit_test_collection__pk=self.kwargs["pk"])


#============================================================================
class InProgress(TestListInstances):
    """view for grouping all test lists with a certain frequency for all units"""
    queryset = models.TestListInstance.objects.in_progress
    #----------------------------------------------------------------------
    def get_page_title(self):
        return "In Progress Test Lists"

#============================================================================
class Unreviewed(TestListInstances):
    """view for grouping all test lists with a certain frequency for all units"""
    queryset = models.TestListInstance.objects.unreviewed
    #----------------------------------------------------------------------
    def get_page_title(self):
        return "Unreviewed Test Lists"

#============================================================================
class ExportToCSV(View):
    """A simple api wrapper to give exported api data a filename for downloads"""

    #----------------------------------------------------------------------
    def get(self,request, *args, **kwargs):
        """takes request, passes it to api and returns a file"""
        response = ValueResource().get_list(request)
        response["Content-Disposition"] = 'attachment; filename=exported_data.csv'
        return response


#============================================================================
class DueDateOverview(TemplateView):
    """Overall status of the QA Program"""
    template_name = "qa/overview_by_due_date.html"
    #----------------------------------------------------------------------
    def get_queryset(self):

        qs = models.UnitTestCollection.objects.filter(
            active=True,
            visible_to__in = self.request.user.groups.all(),
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
        ).order_by("frequency__nominal_interval","unit__number","testlist__name","testlistcycle__name",)

        return qs.distinct()

    #----------------------------------------------------------------------
    def get_context_data(self):
        context = super(DueDateOverview,self).get_context_data()
        qs = self.get_queryset()
        now = timezone.localtime(timezone.datetime.now())

        today = now.date()
        friday = today + timezone.timedelta(days=(4-today.weekday()) % 7 )
        next_friday = friday + timezone.timedelta(days=7)
        month_end = timezone.datetime(now.year, now.month, calendar.mdays[now.month]).date()
        next_month_start = month_end + timezone.timedelta(days=1)
        next_month_end = timezone.datetime(next_month_start.year, next_month_start.month, calendar.mdays[next_month_start.month]).date()

        due = collections.defaultdict(list)
        due_display_order = (
            ("overdue","Due & Overdue"),
            ("this_week","Due This Week"),
            ("next_week","Due Next Week"),
            ("this_month","Due This Month"),
            ("next_month","Due Next Month"),
            #("later","Later"),
        )

        for utc in qs:
            if utc.last_instance:
                due_date = utc.due_date().date()
                if  due_date <= today:
                    due["overdue"].append(utc)
                elif due_date <= friday:
                    if utc.last_instance.work_completed.date() != today:
                        due["this_week"].append(utc)
                elif due_date <= next_friday:
                    due["next_week"].append(utc)
                elif due_date <= month_end:
                    due["this_month"].append(utc)
                elif due_date <= next_month_end:
                    due["next_month"].append(utc)
                else:
                    due["later"].append(utc)
            else:
                due["new"].append(utc)

        ordered_due_lists = []
        for key,display in due_display_order:
            ordered_due_lists.append((display,due[key]))
        context["due"] = ordered_due_lists
        return context

#============================================================================
class Overview(TemplateView):
    """Overall status of the QA Program"""
    template_name = "qa/overview.html"
    #----------------------------------------------------------------------
    def get_queryset(self):

        qs = models.UnitTestCollection.objects.filter(
            active=True,
            visible_to__in = self.request.user.groups.all(),
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
        ).order_by("frequency__nominal_interval","unit__number","testlist__name","testlistcycle__name",)

        return qs.distinct()

    #----------------------------------------------------------------------
    def get_context_data(self):
        context = super(Overview,self).get_context_data()
        qs = self.get_queryset()
        now = timezone.localtime(timezone.datetime.now())

        today = now.date()
        friday = today + timezone.timedelta(days=(4-today.weekday()) % 7 )
        next_friday = friday + timezone.timedelta(days=7)
        month_end = timezone.datetime(now.year, now.month, calendar.mdays[now.month]).date()
        next_month_start = month_end + timezone.timedelta(days=1)
        next_month_end = timezone.datetime(next_month_start.year, next_month_start.month, calendar.mdays[next_month_start.month]).date()

        units = Unit.objects.order_by("number")
        frequencies = models.Frequency.objects.order_by("nominal_interval")

        due = collections.defaultdict(list)
        unit_lists = []

        for unit in units:
            unit_lists.append((unit,[]))
            for freq in frequencies:
                unit_lists[-1][-1].append((freq,[utc for utc in qs if utc.frequency == freq and utc.unit == unit]))

        context["unit_lists"] = unit_lists
        return context