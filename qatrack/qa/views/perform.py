import json
import math
import os
import shutil


import numpy
import scipy
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import View, ListView, CreateView
from django.utils import timezone
from django.utils.translation import ugettext as _

from . import forms
from .. import models, utils, signals
from .base import BaseEditTestListInstance, TestListInstances, UTCList, logger
from qatrack.contacts.models import Contact
from qatrack.units.models import UnitType, Unit

from braces.views import JSONResponseMixin, PermissionRequiredMixin

DEFAULT_CALCULATION_CONTEXT = {
    "math": math,
    "scipy": scipy,
    "numpy": numpy,
}

#---------------------------------------------------------------------------
def process_procedure(procedure):
    """prepare raw calculation procedure for evaluation"""
    return "\n".join(["from __future__ import division", procedure, "\n"]).replace('\r', '\n')

#============================================================================
class Upload(JSONResponseMixin, View):
    """Handle AJAX upload requests"""

    #----------------------------------------------------------------------
    def post(self, *args, **kwargs):
        """calculate and return all composite values"""
        self.handle_upload()

        self.set_calculation_context()

        results = {
            'temp_file_name': self.file_name,
            'success': False,
            'errors': [],
            "result": None,
        }

        try:
            test = models.Test.objects.get(pk=self.request.POST.get("test_id"))
            code = compile(process_procedure(test.calculation_procedure), "<string>", "exec")
            exec code in self.calculation_context
            key = "result" if "result" in self.calculation_context else test.slug
            results["result"] = self.calculation_context[key]
            results["success"] = True
        except models.Test.DoesNotExist:
            results["errors"].append("Test with that ID does not exist")
        except Exception:
            results["errors"].append("Invalid Test")

        return self.render_json_response(results)

    #---------------------------------------------------------------
    @staticmethod
    def get_upload_name(session_id, unit_test_info, name):
        """construct a unique file name for uploaded file"""
        name = name.rsplit(".")
        if len(name) == 1:
            name.append("")
        name, ext = name

        name_parts = (
            name,
            unit_test_info,
            "%s" % (timezone.now().date(),),
            session_id[:6],
        )
        return "_".join(name_parts) + "." + ext

    #----------------------------------------------------------------------
    def handle_upload(self):

        self.file_name = self.get_upload_name(
            self.request.COOKIES.get('sessionid'),
            self.request.POST.get("test_id"),
            self.request.FILES.get("upload").name,
        )

        self.upload = open(os.path.join(settings.TMP_UPLOAD_ROOT, self.file_name), "w+b")

        for chunk in self.request.FILES.get("upload").chunks():
            self.upload.write(chunk)

        self.upload.seek(0)

    #----------------------------------------------------------------------
    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""

        self.calculation_context = {
            "file_object": self.upload,
        }
        self.calculation_context.update(DEFAULT_CALCULATION_CONTEXT)


#============================================================================
class CompositeCalculation(JSONResponseMixin, View):
    """validate all qa tests in the request for the :model:`TestList` with id test_list_id"""

    #----------------------------------------------------------------------
    def get_json_data(self, name):
        """return python data from GET json data"""
        json_string = self.request.POST.get(name)
        if not json_string:
            return

        try:
            return json.loads(json_string)
        except (KeyError, ValueError):
            return

    #----------------------------------------------------------------------
    def post(self, *args, **kwargs):
        """calculate and return all composite values"""

        self.set_composite_test_data()
        if not self.composite_tests:
            return self.render_json_response({"success": False, "errors": ["No Valid Composite ID's"]})

        self.set_calculation_context()
        if not self.calculation_context:
            return self.render_json_response({"success": False, "errors": ["Invalid QA Values"]})

        self.set_dependencies()
        self.resolve_dependency_order()

        results = {}

        for slug in self.cyclic_tests:
            results[slug] = {'value': None, 'error': "Cyclic test dependency"}

        for slug in self.calculation_order:
            raw_procedure = self.composite_tests[slug]
            procedure = process_procedure(raw_procedure)
            try:
                code = compile(procedure, "<string>", "exec")
                exec code in self.calculation_context
                key = "result" if "result" in self.calculation_context else slug
                result = self.calculation_context[key]

                results[slug] = {'value': result, 'error': None}
                self.calculation_context[slug] = result
            except Exception:
                results[slug] = {'value': None, 'error': "Invalid Test"}
            finally:
                if "result" in self.calculation_context:
                    del self.calculation_context["result"]

        return self.render_json_response({"success": True, "errors": [], "results": results})

    #----------------------------------------------------------------------
    def set_composite_test_data(self):

        composite_ids = self.get_json_data("composite_ids")

        if composite_ids is None:
            self.composite_tests = {}
            return

        composite_tests = models.Test.objects.filter(
            pk__in=composite_ids
        ).values_list("slug", "calculation_procedure")

        self.composite_tests = dict(composite_tests)

    #----------------------------------------------------------------------
    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""
        values = self.get_json_data("qavalues")
        upload_data = self.get_json_data("upload_data")

        if values is None and upload_data is None:
            self.calculation_context = {}
            return

        self.calculation_context = {"uploads": upload_data,}

        self.calculation_context.update(DEFAULT_CALCULATION_CONTEXT)

        for slug, val in values.iteritems():
            if slug not in self.composite_tests:
                self.calculation_context[slug] = val
                #try:
                #    self.calculation_context[slug] = float(val)
                #except (ValueError, TypeError):

    #----------------------------------------------------------------------
    def set_dependencies(self):
        """figure out composite dependencies of composite tests"""

        self.dependencies = {}
        slugs = self.composite_tests.keys()
        for slug in slugs:
            tokens = utils.tokenize_composite_calc(self.composite_tests[slug])
            dependencies = [s for s in slugs if s in tokens and s != slug]
            self.dependencies[slug] = set(dependencies)

    #----------------------------------------------------------------------
    def resolve_dependency_order(self):
        """resolve calculation order dependencies using topological sort"""
        # see http://code.activestate.com/recipes/577413-topological-sort/
        data = dict(self.dependencies)
        for k, v in data.items():
            v.discard(k)  # Ignore self dependencies
        extra_items_in_deps = reduce(set.union, data.values()) - set(data.keys())
        data.update(dict((item, set()) for item in extra_items_in_deps))
        deps = []
        while True:
            ordered = set(item for item, dep in data.items() if not dep)
            if not ordered:
                break
            deps.extend(list(sorted(ordered)))
            data = dict((item, (dep - ordered)) for item, dep in data.items() if item not in ordered)

        self.calculation_order = deps
        self.cyclic_tests = data.keys()


#====================================================================================
class ChooseUnit(ListView):
    """choose a unit to perform qa on for this session"""
    model = UnitType
    context_object_name = "unit_types"

    #---------------------------------------------------------------------------
    def get_queryset(self):
        groups = self.request.user.groups.all()
        units = list(set(models.UnitTestCollection.objects.by_visibility(groups).values_list("unit", flat=True)))
        return UnitType.objects.all().filter(unit__pk__in=units).order_by("unit__number").prefetch_related("unit_set")

    #----------------------------------------------------------------------
    def get_context_data(self, *args, **kwargs):
        """reorder unit types"""
        context = super(ChooseUnit, self).get_context_data(*args, **kwargs)
        uts = [ut for ut in context["unit_types"] if len(ut.unit_set.all()) > 0]
        context["unit_types"] = utils.unique(uts)
        return context


#============================================================================
class PerformQA(PermissionRequiredMixin, CreateView):
    """view for users to complete a qa test list"""

    permission_required = "qa.add_testlistinstance"
    form_class = forms.CreateTestListInstanceForm
    model = models.TestListInstance

    #----------------------------------------------------------------------
    def set_test_lists(self, current_day):

        self.test_list = self.unit_test_col.get_list(current_day)
        if self.test_list is None:
            raise Http404

        self.all_lists = [self.test_list] + list(self.test_list.sublists.all())

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
                "unit", "frequency", "last_instance"
            ).filter(
                active=True,
                visible_to__in=self.request.user.groups.all(),
            ).distinct(),
            pk=self.kwargs["pk"]
        )

    #----------------------------------------------------------------------
    def set_actual_day(self):
        cycle_membership = models.TestListCycleMembership.objects.filter(
            test_list=self.test_list,
            cycle=self.unit_test_col.tests_object
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
                test_list=self.unit_test_col.last_instance.test_list,
                cycle=self.unit_test_col.tests_object
            )
            if last_membership:
                self.last_day = last_membership[0].order + 1
    #---------------------------------------------------------------
    def template_unit_test_infos(self):
        """prepare the unit test infos for rendering in template"""
        template_utis = []
        for uti in self.unit_test_infos:
            template_utis.append({
                "id": uti.pk,
                "test": model_to_dict(uti.test),
                "reference": model_to_dict(uti.reference) if uti.reference else None,
                "tolerance": model_to_dict(uti.tolerance) if uti.tolerance else None,
            })
        return template_utis
    #----------------------------------------------------------------------
    def set_unit_test_infos(self):
        utis = models.UnitTestInfo.objects.filter(
            unit=self.unit_test_col.unit,
            test__in=self.all_tests,
            active=True,
        ).select_related(
            "reference",
            "test__category",
            "test__pk",
            "tolerance",
            "unit",
        )

        # make sure utis are correctly ordered
        uti_tests = [x.test for x in utis]
        self.unit_test_infos = []
        for test in self.all_tests:
            try:
                self.unit_test_infos.append(utis[uti_tests.index(test)])
            except ValueError:
                msg = "Do not treat! Please call physics.  Test '%s' is missing information for this unit " % test.name
                logger.error(msg + " Test=%d" % test.pk)
                messages.error(self.request, _(msg))

    #----------------------------------------------------------------------
    def add_histories(self, forms):
        """paste historical values onto unit test infos (ugh ugly)"""
        history, history_dates = self.unit_test_col.history()
        self.history_dates = history_dates
        for form in forms:
            for test, hist in history:
                if test == form.unit_test_info.test:
                    form.history = hist
                    break

    #---------------------------------------------------------------------------
    def get_test_status(self, form):
        """return default or user requested test status"""

        try:
            return models.TestInstanceStatus.objects.get(pk=form["status"].value())
        except (KeyError, models.TestInstanceStatus.DoesNotExist):
            return models.TestInstanceStatus.objects.default()

    #----------------------------------------------------------------------
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        for ti_form in formset:
            ti_form.in_progress = form.instance.in_progress

        if not formset.is_valid():
            context["form"] = form
            return self.render_to_response(context)

        status = self.get_test_status(form)

        self.object = form.save(commit=False)
        self.object.test_list = self.test_list
        self.object.unit_test_collection = self.unit_test_col
        self.object.created_by = self.request.user
        self.object.modified_by = self.request.user
        self.object.modified = timezone.now()

        self.object.reviewed= None if status.requires_review else self.object.modified 
        self.object.reviewed_by = None if status.requires_review else self.request.user
        self.object.all_reviewed= not status.requires_review

        if self.object.work_completed is None:
            self.object.work_completed = self.object.modified


        # save here so pk is set when saving test instances
        # and save below to get due deate set ocrrectly
        self.object.save()

        to_save = []

        for ti_form in formset:
            if ti_form.unit_test_info.test.is_upload():
                fname = ti_form.cleaned_data["string_value"]
                src = os.path.join(settings.TMP_UPLOAD_ROOT, fname)
                d = os.path.join(settings.MEDIA_ROOT, "%s" % self.object.pk)
                if not os.path.exists(d):
                    os.mkdir(d)
                dest = os.path.join(settings.MEDIA_ROOT, d, fname)
                shutil.move(src, dest)

            now = timezone.now()

            ti = models.TestInstance(
                value=ti_form.cleaned_data.get("value", None),
                string_value=ti_form.cleaned_data.get("string_value", ""),
                skipped=ti_form.cleaned_data.get("skipped", False),
                comment=ti_form.cleaned_data.get("comment", ""),
                unit_test_info=ti_form.unit_test_info,
                reference=ti_form.unit_test_info.reference,
                tolerance=ti_form.unit_test_info.tolerance,
                status=status,
                created=now,
                created_by=self.request.user,
                modified_by=self.request.user,

                in_progress=self.object.in_progress,
                test_list_instance=self.object,
                work_started=self.object.work_started,
                work_completed=self.object.work_completed,
            )
            ti.calculate_pass_fail()
            to_save.append(ti)

        models.TestInstance.objects.bulk_create(to_save)

        #set due date to account for any non default statuses
        self.object.unit_test_collection.set_due_date()

        if not self.object.in_progress:
            signals.testlist_complete.send(sender=self,instance=self.object, created=False)

        # let user know request succeeded and return to unit list
        messages.success(self.request, _("Successfully submitted %s " % self.object.test_list.name))

        return HttpResponseRedirect(self.get_success_url())

    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):

        context = super(PerformQA, self).get_context_data(**kwargs)

        # explicity refresh session expiry to prevent situation where a session
        # expires in between the time a user requests a page and then submits the page
        # causing them to lose all the data they entered
        self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        if models.TestInstanceStatus.objects.default() is None:
            messages.error(
                self.request, "There must be at least one Test Status defined before performing a TestList"
            )
            return context

        self.set_unit_test_collection()
        self.set_test_lists(self.get_requested_day_to_perform())
        self.set_actual_day()
        self.set_last_day()
        self.set_all_tests()
        self.set_unit_test_infos()

        if self.request.method == "POST":
            formset = forms.CreateTestInstanceFormSet(self.request.POST, self.request.FILES, unit_test_infos=self.unit_test_infos, user=self.request.user)
        else:
            formset = forms.CreateTestInstanceFormSet(unit_test_infos=self.unit_test_infos, user=self.request.user)

        self.add_histories(formset.forms)
        context["formset"] = formset

        context["history_dates"] = self.history_dates
        context['categories'] = set([x.test.category for x in self.unit_test_infos])
        context['current_day'] = self.actual_day + 1
        context["last_instance"] = self.unit_test_col.last_instance
        context['last_day'] = self.last_day
        ndays = len(self.unit_test_col.tests_object)
        if ndays > 1:
            context['days'] = range(1, ndays + 1)

        context["test_list"] = self.test_list
        context["unit_test_infos"] = json.dumps(self.template_unit_test_infos())
        context["unit_test_collection"] = self.unit_test_col
        context["contacts"] = list(Contact.objects.all().order_by("name"))
        return context

    #----------------------------------------------------------------------
    def get_requested_day_to_perform(self):
        """request comes in as 1 based day, convert to zero based"""
        try:
            day = int(self.request.GET.get("day")) - 1
        except (ValueError, TypeError, KeyError):
            day = None
        return day

    #----------------------------------------------------------------------
    def get_success_url(self):
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        kwargs = {
            "unit_number": self.unit_test_col.unit.number,
            "frequency": self.unit_test_col.frequency.slug if self.unit_test_col.frequency else "ad-hoc"
        }

        return reverse("qa_by_frequency_unit", kwargs=kwargs)


#============================================================================
class EditTestListInstance(PermissionRequiredMixin, BaseEditTestListInstance):
    """view for users to complete a qa test list"""

    permission_required = "qa.change_testlistinstance"
    form_class = forms.UpdateTestListInstanceForm
    formset_class = forms.UpdateTestInstanceFormSet

    #----------------------------------------------------------------------
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        for ti_form in formset:
            ti_form.in_progress = form.instance.in_progress

        if formset.is_valid():
            self.object = form.save(commit=False)

            status_pk = None
            if "status" in form.fields:
                status_pk = form["status"].value()
            self.set_status_object(status_pk)

            self.update_test_list_instance()

            for ti_form in formset:
                ti = ti_form.save(commit=False)
                self.update_test_instance(ti)

            self.object.unit_test_collection.set_due_date()

            if not self.object.in_progress:
                signals.testlist_complete.send(sender=self,instance=self.object, created=False)
            # let user know request succeeded and return to unit list
            messages.success(self.request, _("Successfully submitted %s " % self.object.test_list.name))

            return HttpResponseRedirect(self.get_success_url())
        else:
            context["form"] = form
            return self.render_to_response(context)

    #----------------------------------------------------------------------
    def update_test_list_instance(self):
        self.object.created_by = self.request.user
        self.object.modified_by = self.request.user
        now = timezone.now()

        self.object.modified = now
        if self.status.requires_review:
            self.object.reviewed = None
            self.object.reviewed_by = None
            self.object.all_reviewed = False
        else:
            self.reviewed = now
            self.reviewed_by = self.request.user
            self.object.all_reviewed = True

        if self.object.work_completed is None:
            self.object.work_completed = now

        self.object.save()

    #----------------------------------------------------------------------
    def set_status_object(self, status_pk):
        try:
            self.status = models.TestInstanceStatus.objects.get(pk=status_pk)
        except (models.TestInstanceStatus.DoesNotExist, ValueError):
            self.status = models.TestInstanceStatus.objects.default()

    #----------------------------------------------------------------------
    def update_test_instance(self, test_instance):
        ti = test_instance
        ti.status = self.status
        ti.created_by = self.request.user
        ti.modified_by = self.request.user
        ti.in_progress = self.object.in_progress
        ti.work_started = self.object.work_started
        ti.work_completed = self.object.work_completed

        try:
            ti.save()
        except ZeroDivisionError:

            msga = "Tried to calculate percent diff with a zero reference value. "

            ti.skipped = True
            ti.comment = msga + " Original value was %s" % ti.value
            ti.value = None
            ti.save()

            logger.error(msga + " UTI=%d" % ti.unit_test_info.pk)
            msg = "Please call physics.  Test %s is configured incorrectly on this unit. " % ti.unit_test_info.test.name
            msg += msga
            messages.error(self.request, _(msg))

    #---------------------------------------------------------------
    def template_unit_test_infos(self):
        """prepare the unit test infos for rendering in template"""
        template_utis = []
        for uti in self.unit_test_infos:
            template_utis.append({
                "id": uti.pk,
                "test": model_to_dict(uti.test),
                "reference": model_to_dict(uti.reference) if uti.reference else None,
                "tolerance": model_to_dict(uti.tolerance) if uti.tolerance else None,
            })
        return template_utis
    #---------------------------------------------------------------
    def get_context_data(self, **kwargs):
        """"""
        context = super(EditTestListInstance,self).get_context_data(**kwargs)
        self.unit_test_infos =[f.instance.unit_test_info for f in context["formset"]]
        context["unit_test_infos"] = json.dumps(self.template_unit_test_infos())
        return context

class ContinueTestListInstance(EditTestListInstance):

    permission_required = "qa.add_testlistinstance"

#============================================================================
class InProgress(TestListInstances):
    """view for grouping all test lists with a certain frequency for all units"""

    queryset = models.TestListInstance.objects.in_progress

    #----------------------------------------------------------------------
    def get_page_title(self):
        return "In Progress Test Lists"


#============================================================================
class FrequencyList(UTCList):
    """list daily/monthly/annual test lists for a unit"""

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""

        qs = super(FrequencyList, self).get_queryset()

        freqs = self.kwargs["frequency"].split("/")
        self.frequencies = models.Frequency.objects.filter(slug__in=freqs)

        q = Q(frequency__in=self.frequencies)
        if "ad-hoc" in freqs:
            q |= Q(frequency=None)

        return qs.filter(q).distinct()

    #----------------------------------------------------------------------
    def get_page_title(self):
        return ",".join([x.name if x else "ad-hoc" for x in self.frequencies]) + " Test Lists"


#============================================================================
class UnitFrequencyList(FrequencyList):
    """list daily/monthly/annual test lists for a unit"""

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""
        qs = super(UnitFrequencyList, self).get_queryset()
        self.units = Unit.objects.filter(number__in=self.kwargs["unit_number"].split("/"))
        return qs.filter(unit__in=self.units)

    #----------------------------------------------------------------------
    def get_page_title(self):
        title = ", ".join([x.name for x in self.units])
        title += " " + ", ".join([x.name if x else "ad-hoc" for x in self.frequencies]) + " Test Lists"
        return title


#====================================================================================
class UnitList(UTCList):
    """list qa filtered by unit"""

    #----------------------------------------------------------------------
    def get_queryset(self):
        """filter queryset by frequency"""
        qs = super(UnitList, self).get_queryset()
        self.units = Unit.objects.filter(
            number__in=self.kwargs["unit_number"].split("/")
        )
        return qs.filter(unit__in=self.units)

    #----------------------------------------------------------------------
    def get_page_title(self):
        title = ", ".join([x.name for x in self.units]) + " Test Lists"
        return title
