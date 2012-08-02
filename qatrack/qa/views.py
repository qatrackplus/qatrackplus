import json
from api import ValueResource
from django.contrib import messages
from django.forms.models import inlineformset_factory
from django.http import HttpResponse,HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.views.generic import ListView, FormView, View, TemplateView, RedirectView, CreateView
from django.utils.translation import ugettext as _
from django.utils import timezone
from qatrack.qa import models,utils
from qatrack.units.models import Unit, UnitType
from qatrack import settings

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
class ControlChartImage(View):
    """Return a control chart image from given qa data"""
    #----------------------------------------------------------------------
    def get_dates(self):
        """try to parse from_date & to_date from GET parameters"""

        from_date = self.request.GET.get("from_date",None)
        to_date = self.request.GET.get("to_date",None)

        try:
            to_date = timezone.datetime.strptime(to_date,settings.SIMPLE_DATE_FORMAT)
            to_date = timezone.make_aware(to_date,timezone.get_current_timezone())
        except:
            to_date = timezone.now()

        try:
            from_date = timezone.datetime.strptime(from_date,settings.SIMPLE_DATE_FORMAT)
            from_date = timezone.make_aware(from_date,timezone.get_current_timezone())
        except:
            from_date = to_date - timezone.timedelta(days=30)

        return from_date,to_date
    #----------------------------------------------------------------------
    def get_test(self):
        """return first requested test for control chart others are ignored"""
        return self.request.GET.get("slug","").split(",")[0]
    #----------------------------------------------------------------------
    def get_units(self):
        """return first unit requested, others are ignored"""
        return self.request.GET.get("unit","").split(",")[0]
    #----------------------------------------------------------------------
    def get_data(self):
        """grab data to create control chart from"""
        from_date, to_date = self.get_dates()

        test = self.get_test()

        unit = self.get_units()

        if not all([from_date,to_date,test,unit]):
            return [], []

        data = models.TestInstance.objects.complete().filter(
            test__slug = test,
            work_completed__gte = from_date,
            work_completed__lte = to_date,
            unit__number = unit,
        ).order_by("work_completed","pk").values_list("work_completed","value")

        if data.count()>0:
            return zip(*data)
        return [],[]

    #----------------------------------------------------------------------
    def get(self,request):
        return self.render_to_response({})
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
            im = open(os.path.join(settings.PROJECT_ROOT,"qa","static","img","control_charts_not_available.png"),"rb").read()
            return HttpResponse(im,mimetype="image/png")


        fig=Figure(dpi=72,facecolor="white")
        dpi = fig.get_dpi()
        fig.set_size_inches(
            self.get_number_from_request("width",700)/dpi,
            self.get_number_from_request("height",480)/dpi,
        )
        canvas=FigureCanvas(fig)

        dates,data = self.get_data()

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
        for name, procedure in self.composite_tests:
            #set up clean calculation context each time so there
            #is no potential conflicts between different composite tests
            self.set_calculation_context()
            procedure = "\n".join(["from __future__ import division",procedure])
            try:
                code = compile(procedure,"<string>","exec")
                exec code in self.calculation_context
                results[name] = {
                    'value':self.calculation_context.pop("result"),
                    'error':None
                }
            except:
                results[name] = {'value':None, 'error':"Invalid Test"}

        return self.render_to_response({"success":True,"errors":[],"results":results})

    #----------------------------------------------------------------------
    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""


        self.calculation_context = {}
        self.calculation_context["math"] = math

        for slug,info in self.values.iteritems():
            val = info["current_value"]
            if val is not None:
                try:
                    self.calculation_context[slug] = float(val)
                except ValueError:
                    pass

#====================================================================================
class ChooseUnit(ListView):
    """choose a unit to perform qa on for this session"""
    model = Unit
    context_object_name = "units"
    template_name = "choose_unit.html"



#============================================================================
class PerformQAView(CreateView):
    """view for users to complete a qa test list"""
    template_name = "perform_test_list.html"
    form_class = forms.TestListInstanceForm

    TEST_LIST_TO_TEST_TRANSFER_FIELDS = (
        "unit",
        "created_by",
        "modified_by",
        "work_started",
        "work_completed",
        "in_progress"
    )

    #----------------------------------------------------------------------
    def create_new_test_list_instance(self):
        """generate a new test list instance for the user to fill in values for"""
        self.test_list_instance = models.TestListInstance(
            test_list   = self.test_list,
            unit        = self.unit_test_list.unit,
            created_by  = self.request.user,
            modified_by = self.request.user,
        )


    #----------------------------------------------------------------------
    def add_test_instances(self):
        """create new test instances"""
        all_lists = [self.test_list]+list(self.test_list.sublists.all())
        default_status = models.TestInstanceStatus.objects.default()

        all_tests = []
        for test_list in all_lists:
            tests = test_list.tests.all().order_by("testlistmembership__order")
            all_tests.extend(tests)
        
        utis = models.UnitTestInfo.objects.filter(
            unit = self.unit_test_list.unit,
            test__in = all_tests,
            frequency=self.unit_test_list.frequency,
            active=True,
        ).select_related(
            "reference",
            "tolerance",
            "test",
            "unit",
            "test__category",
        )
        
        uti_d = {}
        
        for uti in utis:
            ti = models.TestInstance(
                test = uti.test,
                reference = uti.reference,
                tolerance = uti.tolerance,
                status = default_status,
                unit = self.unit_test_list.unit,
                created_by = self.request.user,
                modified_by = self.request.user,
                in_progress = self.test_list_instance.in_progress,
                test_list_instance=self.test_list_instance
            )
            uti_d[uti.test.pk] = (ti,uti.history())
            
        #reorder in order of tests rather than order utis were returned from db
        self.test_instances = [uti_d[x.pk] for x in all_tests]

    #----------------------------------------------------------------------
    def create_formset_class(self):
        return inlineformset_factory(
            models.TestListInstance,
            models.TestInstance,
            form=forms.TestInstanceForm,
            formset=forms.BaseTestInstanceFormset,
            extra = self.test_list.all_tests().count()
        )

    #----------------------------------------------------------------------
    def copy_values(self,test_list_instance,test_instance):
        for field in self.TEST_LIST_TO_TEST_TRANSFER_FIELDS:
            setattr(test_instance,field,getattr(test_list_instance,field))
    #----------------------------------------------------------------------
    def form_valid(self,form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            self.object = form.save(commit=False)
            self.object.test_list = self.test_list
            self.object.unit = self.unit_test_list.unit
            self.object.created_by = self.request.user
            self.object.modified_by= self.request.user
            if self.object.work_completed is None:
                self.object.work_completed = timezone.now()
            self.object.save()

            status = models.TestInstanceStatus.objects.default()
            if form.fields.has_key("status"):
                status_pk = form["status"].value()
                if status_pk:
                    status = models.TestInstanceStatus.objects.get(pk=status_pk)

            for ti_form in formset:
                ti_form.instance.status = status
                ti_form.instance.test_list_instance = self.object
                self.copy_values(self.object,ti_form.instance)
                ti_form.save()


            #let user know request succeeded and return to unit list
            messages.success(self.request,_("Successfully submitted %s "% self.object.test_list.name))

            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):
        context = super(PerformQAView,self).get_context_data(**kwargs)
        if models.TestInstanceStatus.objects.default() is None:
            messages.error(
                self.request,"There must be at least one Test Status defined before performing a TestList"
            )
            return context
        
        q = models.UnitTestCollection.objects.select_related(
            "unit",
            "frequency",
        ).filter(pk=self.kwargs["pk"])
        
        if q.count() == 0:
            raise Http404        
        self.unit_test_list = q[0]
        
        
        current_day = self.get_day_to_perform()        
        self.test_list = self.unit_test_list.get_list(current_day)        
        if self.test_list is None:
            raise Http404
        

        
        self.create_new_test_list_instance()
        self.add_test_instances()
            
            
        TestInstanceFormset = self.create_formset_class()

        if self.request.method == "POST":
            formset = TestInstanceFormset(self.request.POST,self.request.FILES,)
        else:
            formset = TestInstanceFormset()
            for subform, (ti,hist) in zip(formset.forms,self.test_instances):
                subform.initial = forms.model_to_dict(ti)

        for subform, (ti,hist) in zip(formset.forms,self.test_instances):
            subform.instance = ti
            subform.history = hist
            subform.setup_form()


        context["formset"] = formset
        context["include_admin"] = self.request.user.is_staff
        context['categories'] = set([x[0].test.category for x in self.test_instances])
        context['current_day'] = current_day
        context['days'] = range(1,len(self.unit_test_list.tests_object)+1)
        context["unit_test_list"] = self.unit_test_list


        return context
        
    #----------------------------------------------------------------------
    def get_day_to_perform(self):
        """request comes in as 1 based day, convert to zero based"""
        try:
            day = int(self.request.GET.get("day"))-1
        except (ValueError,TypeError,KeyError):
            day = None
        return day
    #----------------------------------------------------------------------
    def get_success_url(self):
        kwargs = {
            "unit_number":self.unit_test_list.unit.number,
            "frequency":self.unit_test_list.frequency.slug
        }
        return reverse("qa_by_frequency_unit",kwargs=kwargs)


#============================================================================
class UnitFrequencyListView(ListView):
    """list daily/monthly/annual test lists for a unit"""

    template_name = "frequency_list.html"
    context_object_name = "unittestcollections"

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""
        return models.UnitTestCollection.objects.filter(
            frequency__slug=self.kwargs["frequency"],
            unit__number=self.kwargs["unit_number"],
            active=True,
        )


#============================================================================
class UnitGroupedFrequencyListView(ListView):
    """view for grouping all test lists with a certain frequency for all units"""
    template_name = "unit_grouped_frequency_list.html"
    context_object_name = "unittestcollections"

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""

        return models.UnitTestCollection.objects.filter(
            frequency__slug=self.kwargs["frequency"],
            active=True,
        )
#============================================================================
class AllTestCollections(ListView):
    """show all lists currently assigned to the groups this member is a part of"""

    template_name = "all_test_lists.html"
    context_object_name = "unittestcollections"
    #----------------------------------------------------------------------
    def get_queryset(self):
        return models.UnitTestCollection.objects.filter(active=True)


#============================================================================
class ChartView(TemplateView):
    """view for creating charts/graphs from data"""
    template_name = "charts.html"
    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):
        """add default dates to context"""
        context = super(ChartView,self).get_context_data(**kwargs)
        context["from_date"] = timezone.now().date()-timezone.timedelta(days=365)
        context["to_date"] = timezone.now().date()+timezone.timedelta(days=1)
        context["check_list_filters"] = [
            ("Frequency","frequency"),
            ("Review Status","review-status"),
            ("Unit","unit"),
            ("Category","category"),
            ("Test List","test-list"),
            ("Test","test"),
        ]
        return context


#============================================================================
class ReviewView(ListView):
    """view for grouping all test lists with a certain frequency for all units"""
    template_name = "review_all.html"
    model = models.UnitTestCollection
    context_object_name = "unittestcollections"


#============================================================================
class ExportToCSV(View):
    """A simple api wrapper to give exported api data a filename for downloads"""

    #----------------------------------------------------------------------
    def get(self,request, *args, **kwargs):
        """takes request, passes it to api and returns a file"""
        response = ValueResource().get_list(request)
        response["Content-Disposition"] = 'attachment; filename=exported_data.csv'
        return response
