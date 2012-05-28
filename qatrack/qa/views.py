import json
from django.contrib import messages
from django.http import HttpResponse,HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.views.generic import ListView, FormView, View, TemplateView, RedirectView
from django.utils.translation import ugettext as _
from django.utils import timezone
from qatrack.qa import models
from qatrack.units.models import Unit, UnitType
from qatrack import settings
from qatrack.qagroups.models import GroupProfile
import forms
import math

#TODO: Move location of qa/template.html templates (up one level)

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
class UserHome(RedirectView):
    """redirect a user to their appropriate home page"""

    #----------------------------------------------------------------------
    def get_redirect_url(self,**kwargs):
        """guess redirect url based on user permissions"""
        groups = self.request.user.groups.all()
        if groups.count()>0:
            profile = groups[0].groupprofile
            if profile:
                return profile.homepage
        return "/"

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
    def post(self,request, *args, **kwargs):
        """calculate and return all composite values
        Note we use post here because the query strings can get very long and
        we may run into browser limits with GET.
        """
        self.values = self.get_json_data("qavalues")
        if not self.values:
            self.render_to_response({"success":False,"errors":["Invalid QA Values"]})

        self.composite_ids = self.get_json_data("composite_ids")
        if not self.composite_ids:
            return self.render_to_response({"success":False,"errors":["No Valid Composite ID's"]})

        #grab calculation procedures for all the composite tests
        self.composite_tests = models.Test.objects.filter(
            pk__in=self.composite_ids.values()
        ).values_list("short_name", "calculation_procedure")


        results = {}
        for name, procedure in self.composite_tests:
            #set up clean calculation context each time so there
            #is no potential conflicts between different composite tests
            self.set_calculation_context()
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

        self.calculation_context = {
            'math':math,
        }

        for short_name,info in self.values.iteritems():
            val = info["current_value"]
            if val is not None:
                try:
                    self.calculation_context[short_name] = float(val)
                except ValueError:
                    pass

#============================================================================
class PerformQAView(FormView):
    """view for users to complete a qa test list"""
    template_name = "perform_test_list.html"

    context_object_name = "test_list"
    form_class = forms.TestListInstanceForm
    test_list_fields_to_copy = ("unit", "work_completed", "created", "created_by", "modified", "modified_by",)
    #----------------------------------------------------------------------
    def form_valid(self, form):
        """add extra info to the test_list_intance and save all the tests if valid"""

        context = self.get_context_data(form=form)
        test_list = context["test_list"]
        formset = context["formset"]

        if formset.is_valid():

            #add extra info for test_list_instance
            test_list_instance = form.save(commit=False)
            test_list_instance.test_list = test_list
            test_list_instance.created_by = self.request.user
            test_list_instance.modified_by = self.request.user
            test_list_instance.unit = context["unit"]
            if test_list_instance.work_completed is None:
                test_list_instance.work_completed = timezone.now()
            test_list_instance.save()


            #all test values are validated so now add remaining fields manually and save
            for test_form in formset:
                obj = test_form.save(commit=False)
                obj.test_list_instance = test_list_instance
                for field in self.test_list_fields_to_copy:
                    setattr(obj,field,getattr(test_list_instance,field))
                if form.fields.has_key("status"):
                    obj.status = form["status"].value()
                else:
                    obj.status = models.UNREVIEWED
                obj.save()

            #let user know request succeeded and return to unit list
            messages.success(self.request,_("Successfully submitted %s "% test_list.name))

            return HttpResponseRedirect(reverse("user_home"))

        #there was an error in one of the forms
        return self.render_to_response(context)

    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        """add formset and test list to our template context"""
        context = super(PerformQAView, self).get_context_data(**kwargs)
        unit = get_object_or_404(Unit,number=self.kwargs["unit_number"])

        include_admin = self.request.user.is_staff


        if self.kwargs["type"] == "cycle":
            cycle = get_object_or_404(models.TestListCycle,pk=self.kwargs["pk"])
            day = self.request.GET.get("day")
            if day == "next":
                cycle_membership = cycle.next_for_unit(unit)
            else:
                try:
                    order = int(day)-1
                except (ValueError,TypeError):
                    raise Http404

                cycle_membership = get_object_or_404(
                    models.TestListCycleMembership,
                    cycle = cycle,
                    order=order,
                )

            test_list = cycle_membership.test_list
            current_day = cycle_membership.order + 1
            days = range(1,len(cycle)+1)
        else:
            cycle, current_day,days = None, 1,[]
            test_list =  get_object_or_404(models.TestList,pk=self.kwargs["pk"])

        if self.request.POST:
            formset = forms.TestInstanceFormset(test_list,unit, self.request.POST)
        else:
            formset = forms.TestInstanceFormset(test_list, unit)

        categories = models.Category.objects.all()

        context.update({
            'frequency':self.kwargs["frequency"],
            'current_day':current_day,
            'days':days,
            'test_list':test_list,
            'unit':unit,
            'formset':formset,
            'categories':categories,
            'unit':unit,
            'cycle':cycle,
            'include_admin':include_admin
        })

        return context

#============================================================================
class UnitFrequencyListView(TemplateView):
    """list daily/monthly/annual test lists for a unit"""

    template_name = "frequency_list.html"

    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):
        """
        return test lists and cycles for a specific frequency
        (daily/monthly etc)and specific unit
        """

        context = super(UnitFrequencyListView,self).get_context_data(**kwargs)
        frequency = self.kwargs["frequency"].lower()
        context["frequency"] = frequency

        unit_number = self.kwargs["unit_number"]
        context["unit_test_list"] = models.UnitTestLists.objects.get(unit__number=unit_number,frequency=frequency)

        return context

#============================================================================
class UnitGroupedFrequencyListView(TemplateView):
    """view for grouping all test lists with a certain frequency for all units"""
    template_name = "unit_grouped_frequency_list.html"

    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):
        """grab all test lists and cycles with given frequency"""
        context = super(UnitGroupedFrequencyListView,self).get_context_data(**kwargs)
        frequency = self.kwargs["frequency"].lower()
        context["frequency"] = frequency

        unit_type_sets = []

        for ut in UnitType.objects.all():
            unit_type_set = []
            for unit in ut.unit_set.all():
                unit_type_set.extend(
                    unit.unittestlists_set.filter(frequency=frequency)
                )

            unit_type_sets.append((ut,unit_type_set))

        context["unit_type_list"] = unit_type_sets
        return context

#============================================================================
class UserBasedTestLists(TemplateView):
    """show all lists currently assigned to the groups this member is a part of"""

    template_name = "user_based_test_lists.html"

    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):
        """set frequencies and lists"""
        context = super(UserBasedTestLists,self).get_context_data(**kwargs)

        user_test_lists = []

        group = None
        utls = models.UnitTestLists.objects.all()
        if self.request.user.groups.count() > 0:
            group = self.request.user.groups.all()[0]
            utls = utls.filter(test_lists__assigned_to = group.groupprofile)

        for utl in utls:

            test_lists = utl.test_lists
            cycles = utl.cycles
            if group:
                test_lists = test_lists.filter(assigned_to=group.groupprofile)
                cycles = utl.cycles.filter(assigned_to=group.groupprofile)

            for tl in list(test_lists.all())+list(cycles.all()):
                next_tl = tl
                if isinstance(tl, models.TestListCycle):
                    next_tl = tl.next_for_unit(utl.unit)

                last = tl.last_completed_instance(utl.unit)
                last_done = last.work_completed if last else None

                due_date = models.due_date(utl.unit,next_tl)
                user_test_lists.append((utl,next_tl,last_done,due_date))

        table_headers = ["Unit","Frequency","Test List", "Last Done", "Due Date"]

        context["table_headers"] = table_headers
        context["group"] = group
        context["test_lists"] = user_test_lists
        return context

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
class ReviewView(TemplateView):
    """view for grouping all test lists with a certain frequency for all units"""
    template_name = "review_all.html"

    #----------------------------------------------------------------------
    def get_context_data(self,**kwargs):
        """grab all test lists and cycles with given frequency"""
        context = super(ReviewView,self).get_context_data(**kwargs)

        units = Unit.objects.all()
        frequencies = models.FREQUENCY_CHOICES[:3]
        unit_lists = []
        for unit in units:
            unit_list = []
            for freq, _ in frequencies:
                freq_list = []
                unit_test_lists = unit.unittestlists_set.filter(frequency=freq)

                for utls in unit_test_lists:
                    freq_list.extend(utls.all_test_lists(with_last_instance=True))

                unit_list.append((freq,freq_list))
            unit_lists.append((unit,unit_list))
        context["table_headers"] = [
            "Unit", "Frequency", "Test List",
            "Completed", "Due Date", "Status",
            "Review Status"
        ]
        fdisplay = dict(models.FREQUENCY_CHOICES)
        table_data = []
        for utl in models.UnitTestLists.objects.all():
            unit, frequency = utl.unit, utl.frequency
            data = []

            for test_list,last in utl.all_test_lists(with_last_instance=True):
                last_done, status = ["New List"]*2
                review = ()
                if last is not None:
                    last_done = last.work_completed
                    status = last.pass_fail_status()
                    reviewed = last.testinstance_set.exclude(status=models.UNREVIEWED).count()
                    total = last.testinstance_set.count()
                    if total == reviewed:
                        review = (last.modified_by,last.modified)

                due_date = models.due_date(utl.unit, test_list)
                data = {
                    "info": {
                        "unit_number":unit.number,
                        "test_list_id":test_list.pk,
                        "frequency":frequency,
                        "due":due_date.isoformat() if due_date else ""
                    },
                    "attrs": [
                        #(name, obj, display)
                        ("unit",unit.name),
                        ("frequency",fdisplay[frequency]),
                        ("test_list",test_list.name),
                        ("last_done",last_done),
                        ("due",due_date),
                        ("pass_fail_status",status),
                        ("review_status",review),
                    ]
                }

                if data:
                    table_data.append(data)
        context["data"] = table_data
        context["unit_test_lists"] = models.UnitTestLists.objects.all()
        context["unit_lists"] = unit_lists
        context["units"] = units
        context["routine_freq"] = frequencies
        return context

from api import ValueResource
#============================================================================
class ExportToCSV(View):
    """A simple api wrapper to give exported api data a filename for downloads"""

    #----------------------------------------------------------------------
    def get(self,request, *args, **kwargs):
        """takes request, passes it to api and returns a file"""
        response = ValueResource().get_list(request)
        response["Content-Disposition"] = 'attachment; filename=exported_data.csv'
        return response
