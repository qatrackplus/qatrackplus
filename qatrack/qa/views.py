import collections
import json
from api import ValueResource
from django.contrib import messages
from django.forms.models import inlineformset_factory
from django.http import HttpResponse,HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.views.generic import ListView, UpdateView, View, TemplateView, CreateView, DetailView
from django.utils.translation import ugettext as _
from django.utils import timezone
from qatrack.qa import models,utils
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
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)


#============================================================================
class ChartView(TemplateView):
    """view for creating charts/graphs from data"""
    template_name = "qa/charts.html"

    #----------------------------------------------------------------------
    def create_test_data(self):

        self.test_data = {
            "test_lists":{},
            "tests":{},
            "categories":{}
        }
        for test_list in self.test_lists:
            tests = [x.pk for x in test_list.tests.all()]
            if tests:
                self.test_data["test_lists"][test_list.pk] = {
                    "tests" : tests,
                }
        for test in self.tests:
            test["frequency"] = test["unittestinfo__frequency"]
            self.test_data["tests"][test["pk"]] = test


        return json.dumps(self.test_data)

    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):
        """add default dates to context"""
        context = super(ChartView,self).get_context_data(**kwargs)



        self.test_lists = models.TestList.objects.order_by("name").prefetch_related(
            "tests"
        ).all()

        self.tests = models.Test.objects.order_by("name").values(
            "pk",
            "category",
            "name",
            "type",
            "description",
            "unittestinfo__frequency"
        ).distinct()



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
            "test_data": self.create_test_data(),
            "chart_data_url":reverse("chart_data"),
            "control_chart_url":reverse("control_chart"),

        }
        context.update(c)
        return context

class BaseChartView(View):
    ISO_FORMAT = False
    #----------------------------------------------------------------------
    def get(self,request):

        return self.render_to_response(self.get_plot_data())
    
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
        statuses = self.request.GET.getlist("statuses[]",[])
        now = timezone.datetime.now()
        from_date = self.get_date("from_date",now-timezone.timedelta(days=180))
        to_date = self.get_date("to_date",now)

        tis = models.TestInstance.objects.filter(
            unit_test_info__test__pk__in=tests,
            unit_test_info__unit__pk__in=units,
            status__pk__in = statuses,
            work_completed__gte = from_date,
            work_completed__lte = to_date,
        ).order_by(
            "work_completed"
        )

        data = collections.defaultdict(lambda : {"data":[],"values":[],"dates":[]})
        for ti in tis:
            uti = ti.unit_test_info
            d = timezone.make_naive(ti.work_completed,timezone.get_current_timezone())
            d = self.convert_date(d)
            data[uti.pk]["data"].append([d,ti.value])
            data[uti.pk]["values"].append(ti.value)
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

        if context:
            d = context.values()[0]
            dates,data = d["dates"],d["values"]

        n_baseline_subgroups = self.get_number_from_request("n_baseline_subgroups",2,dtype=int)

        subgroup_size = self.get_number_from_request("subgroup_size",2,dtype=int)
        if subgroup_size <1 or subgroup_size >100:
            subgroup_size = 1

        include_fit = self.request.GET.get("fit_data",False)
        if include_fit == "true":
            include_fit = True


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
        """calculate and return all composite values
        Note we use post here because the query strings can get very long and
        we may run into browser limits with GET.
        """
        self.values = self.get_json_data("qavalues")
        if not self.values:
            return self.render_to_response({"success":False,"errors":["Invalid QA Values"]})

        self.composite_ids = self.get_json_data("composite_ids")
        if not self.composite_ids:
            return self.render_to_response({"success":False,"errors":["No Valid Composite ID's"]})

        #grab calculation procedures for all the composite tests
        self.composite_tests = models.Test.objects.filter(
            pk__in=self.composite_ids.values()
        ).values_list("slug", "calculation_procedure")


        results = {}
        for slug, raw_procedure in self.composite_tests:
            calculation_context = self.get_calculation_context()
            procedure = self.process_procedure(raw_procedure)
            try:
                code = compile(procedure,"<string>","exec")
                exec code in calculation_context
                results[slug] = {
                    'value':calculation_context["result"],
                    'error':None
                }
            except Exception as e:
                results[slug] = {'value':None, 'error':"Invalid Test"}

        return self.render_to_response({"success":True,"errors":[],"results":results})
    #---------------------------------------------------------------------------
    def process_procedure(self,procedure):
        """prepare raw procedure for evaluation"""
        return "\n".join(["from __future__ import division",procedure,"\n"]).replace('\r','\n')
    #----------------------------------------------------------------------
    def get_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""
        context = {
            "math":math
        }

        for slug,info in self.values.iteritems():
            val = info["current_value"]
            if val is not None:
                try:
                    context[slug] = float(val)
                except ValueError:
                    pass
        return context

#====================================================================================
class ChooseUnit(ListView):
    """choose a unit to perform qa on for this session"""
    model = Unit
    context_object_name = "units"

    #---------------------------------------------------------------------------
    def get_queryset(self):
        return Unit.objects.all().select_related("type")


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
                "unit","frequency"
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
        if cycle_membership:
            self.actual_day = cycle_membership[0].order
    #----------------------------------------------------------------------
    def set_unit_test_infos(self):
        self.unit_test_infos = models.UnitTestInfo.objects.filter(
            unit = self.unit_test_col.unit,
            test__in = self.all_tests,
            frequency=self.unit_test_col.frequency,
            active=True,
        ).select_related(
            "reference",
            "test__category",
            "test__pk",
            "tolerance",
            "unit",
        )

        self.add_histories()
    #----------------------------------------------------------------------
    def add_histories(self):
        """paste historical values onto unit test infos"""

        from_date = timezone.make_aware(timezone.datetime.now() - timezone.timedelta(days=10*self.unit_test_col.frequency.overdue_interval),timezone.get_current_timezone())
        histories = utils.tests_history(self.all_tests,self.unit_test_col.unit,from_date)
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
                if val is not None:
                    status = models.TestInstanceStatus.objects.get(pk=val)

            for ti_form in formset:
                ti = models.TestInstance(
                    value=ti_form.cleaned_data["value"],
                    skipped=ti_form.cleaned_data["skipped"],
                    comment=ti_form.cleaned_data["comment"],
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

        if models.TestInstanceStatus.objects.default() is None:
            messages.error(
                self.request,"There must be at least one Test Status defined before performing a TestList"
            )
            return context

        self.set_unit_test_collection()
        self.set_test_lists(self.get_requested_day_to_perform())
        self.set_actual_day()
        self.set_all_tests()
        self.set_unit_test_infos()


        if self.request.method == "POST":
            formset = forms.CreateTestInstanceFormSet(self.request.POST,self.request.FILES,unit_test_infos=self.unit_test_infos)
        else:
            formset = forms.CreateTestInstanceFormSet(unit_test_infos=self.unit_test_infos)


        context["formset"] = formset

        context["history_dates"] = self.history_dates
        context["include_admin"] = self.request.user.is_staff
        context['categories'] = set([x.test.category for x in self.unit_test_infos])
        context['current_day'] = self.actual_day+1

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
        kwargs = {
            "unit_number":self.unit_test_col.unit.number,
            "frequency":self.unit_test_col.frequency.slug
        }
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
        histories = utils.tests_history(tests,self.object.unit_test_collection.unit,from_date)
        unit_test_infos = [f.instance.unit_test_info for f in forms]
        _, self.history_dates = utils.add_history_to_utis(unit_test_infos,histories)


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
        raise NotImplementedError

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
    #----------------------------------------------------------------------
    def get_success_url(self):
        kwargs = {
            "unit_number":self.object.unit_test_collection.unit.number,
            "frequency":self.object.unit_test_collection.frequency.slug
        }
        return reverse("qa_by_frequency_unit",kwargs=kwargs)

#============================================================================
class EditTestListInstance(BaseEditTestListInstance):
    """view for users to complete a qa test list"""

    form_class = forms.UpdateTestListInstanceForm
    formset_class = forms.UpdateTestInstanceFormSet

    #----------------------------------------------------------------------
    def form_valid(self,form):
        context = self.get_context_data()
        formset = context["formset"]

        update_time = timezone.make_aware(timezone.datetime.now(),timezone.get_current_timezone())
        update_user = self.request.user

        for ti_form in formset:
            ti_form.in_progress = form.instance.in_progress

        if formset.is_valid():

            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.modified_by= self.request.user

            if self.object.work_completed is None:
                self.object.work_completed = timezone.make_aware(timezone.datetime.now(),timezone=timezone.get_current_timezone())

            self.object.save()

            status=models.TestInstanceStatus.objects.default()
            if form.fields.has_key("status"):
                val = form["status"].value()
                if val is not None:
                    status = models.TestInstanceStatus.objects.get(pk=val)

            for ti_form in formset:
                ti = ti_form.save(commit=False)
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

            #let user know request succeeded and return to unit list
            messages.success(self.request,_("Successfully submitted %s "% self.object.test_list.name))

            return HttpResponseRedirect(self.get_success_url())
        else:
            context["form"] = form
            return self.render_to_response(context)


    #----------------------------------------------------------------------
    def get_context_data(self,*args,**kwargs):
        context = super(EditTestListInstance,self).get_context_data(*args,**kwargs)
        context["include_admin"] = self.request.user.is_staff

        return context

    #----------------------------------------------------------------------
    def get_success_url(self):
        return reverse("unreviewed")

#============================================================================
class UTCList(ListView):
    model = models.UnitTestCollection
    context_object_name = "unittestcollections"
    paginate_by = settings.PAGINATE_DEFAULT
    action = "perform"
    action_display = "Perform"
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
            "tests_object",
        ).order_by("unit__number","testlist__name","testlistcycle__name",)

        return qs.distinct()

    #----------------------------------------------------------------------
    def get_page_title(self):
        return "All Test Collections"

    #----------------------------------------------------------------------
    def get_context_data(self,*args,**kwargs):
        context = super(UTCList,self).get_context_data(*args,**kwargs)
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
        return qs.filter(unit__in=self.units)

    #---------------------------------------------------------------------------
    def get_page_title(self):
        return "Review " + ", ".join([x.name for x in self.units]) + " Test Lists"

#====================================================================================
class ChooseUnitForReview(ListView):

    model = Unit
    context_object_name = "units"
    template_name_suffix = "_choose_for_review"
    #---------------------------------------------------------------------------
    def get_queryset(self):
        return Unit.objects.all().select_related("type")

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
class TestListInstances(ListView):
    model = models.TestListInstance
    context_object_name = "test_list_instances"
    paginate_by = settings.PAGINATE_DEFAULT
    queryset = models.TestListInstance.objects.all
    #----------------------------------------------------------------------
    def get_queryset(self):
        return self.fetch_related(self.queryset())
    #----------------------------------------------------------------------
    def fetch_related(self,qs):
        return qs.select_related(
            "test_list__name",
            "unit_test_collection__unit__name",
            "unit_test_collection__frequency__name",
            "created_by"
        ).prefetch_related("testinstance_set")
    #----------------------------------------------------------------------
    def get_page_title(self):
        return "Completed Test Lists"
    #----------------------------------------------------------------------
    def get_context_data(self,*args,**kwargs):
        context = super(TestListInstances,self).get_context_data(*args,**kwargs)
        context["page_title"] = self.get_page_title()
        return context
#====================================================================================
class UTCInstances(TestListInstances):

    #---------------------------------------------------------------------------
    def get_queryset(self):
        utc = get_object_or_404(models.UnitTestCollection,pk=self.kwargs["pk"])
        return self.fetch_related(utc.testlistinstance_set)


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
