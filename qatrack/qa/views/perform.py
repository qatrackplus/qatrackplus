import collections
import json
import math
import os
import shutil
import imghdr


import dateutil
import dicom
import numpy
import scipy
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import View, CreateView, TemplateView
from django.utils import timezone
from django.utils.translation import ugettext as _

from . import forms
from .. import models, utils, signals
from .base import BaseEditTestListInstance, TestListInstances, UTCList, logger
from qatrack.contacts.models import Contact
from qatrack.units.models import Unit
from qatrack.service_log import models as sl_models

from braces.views import JSONResponseMixin, PermissionRequiredMixin
from functools import reduce

DEFAULT_CALCULATION_CONTEXT = {
    "math": math,
    "scipy": scipy,
    "numpy": numpy,
    "dicom": dicom,
}


def process_procedure(procedure):
    """
    Cleans and sets new style division for calculations procedures. Used by
    both the :view:`qa.perform.Upload` &
    :view:`qa.perform.CompositeCalculation` views.

    """

    return "\n".join(["from __future__ import division", procedure, "\n"]).replace('\r', '\n')


def process_file_upload_form(ti_form, test_list_instance):
    """
    Check if test instance form is file upload and move the file out of
    tmp directory if it is
    """

    upload_to_process = (
        ti_form.unit_test_info.test.is_upload()
        and not ti_form.cleaned_data["skipped"]
        and ti_form.cleaned_data["string_value"].strip()
    )

    if upload_to_process:
        fname = ti_form.cleaned_data["string_value"]
        src = os.path.join(settings.TMP_UPLOAD_ROOT, fname)

        if not os.path.exists(src):
            # has already been moved (i.e. we are completing an
            # in progress list or editing an already complete list
            return

        d = os.path.join(settings.UPLOAD_ROOT, "%s" % test_list_instance.pk)
        if not os.path.exists(d):
            os.mkdir(d)

        dest = os.path.join(settings.UPLOAD_ROOT, d, fname)
        shutil.move(src, dest)


class Upload(JSONResponseMixin, View):
    """View for handling AJAX upload requests when performing QA"""

    # use html for IE8's sake :(
    content_type = "text/html"

    def post(self, *args, **kwargs):
        """process file, apply calculation procedure and return results"""
        if self.request.POST.get('filename'):
            self.reprocess()
        else:
            self.handle_upload()

        return self.run_calc()

    def reprocess(self):
        tli = self.request.POST.get("test_list_instance")
        self.file_name = self.request.POST.get("filename")
        try:
            self.upload = open(os.path.join(settings.UPLOAD_ROOT, "%s" % tli, self.file_name), "r+b")
        except IOError:
            self.upload = None

    def run_calc(self):
        self.set_calculation_context()

        results = {
            'temp_file_name': self.file_name,
            'is_image': self.is_image(),
            'success': False,
            'errors': [],
            "result": None,
        }

        if self.upload is None:
            results["errors"] = ["Original file not found. Please re-upload."]
            return self.render_json_response(results)

        try:
            test = models.Test.objects.get(pk=self.request.POST.get("test_id"))
            code = compile(process_procedure(test.calculation_procedure), "<string>", "exec")
            exec(code, self.calculation_context)
            key = "result" if "result" in self.calculation_context else test.slug
            results["result"] = self.calculation_context[key]
            results["success"] = True
        except models.Test.DoesNotExist:
            results["errors"].append("Test with that ID does not exist")
        except Exception as e:
            results["errors"].append("Invalid Test Procedure: %s" % e)

        return self.render_json_response(results)

    @staticmethod
    def get_upload_name(session_id, unit_test_info, name):
        """construct a unique file name for uploaded file"""

        name = name.rsplit(".", 1)
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

    def handle_upload(self):
        """read incoming file and save tmp file to disk ready for processing"""

        self.file_name = self.get_upload_name(
            self.request.COOKIES.get('sessionid'),
            self.request.POST.get("test_id"),
            self.request.FILES.get("upload").name,
        )

        self.upload = open(os.path.join(settings.TMP_UPLOAD_ROOT, self.file_name), "w+b")

        for chunk in self.request.FILES.get("upload").chunks():
            self.upload.write(chunk)

        # rewind to beginning of file so it  can be read correctly by calc procedure
        self.upload.seek(0)

    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""

        meta_data = self.get_json_data("meta")

        for d in ("work_completed", "work_started",):
            try:
                meta_data[d] = dateutil.parser.parse(meta_data[d])
            except (KeyError, AttributeError):
                pass

        refs = self.get_json_data("refs")
        tols = self.get_json_data("tols")

        self.calculation_context = {
            "FILE": open(self.upload.name, "r"),
            "BIN_FILE": self.upload,
            "META": meta_data,
            "REFS": refs,
            "TOLS": tols,
        }
        self.calculation_context.update(DEFAULT_CALCULATION_CONTEXT)

    def get_json_data(self, name):
        """return python data from GET json data"""
        data = self.request.POST

        json_string = data.get(name)
        if not json_string:
            return

        try:
            return json.loads(json_string)
        except (KeyError, ValueError):
            return

    def is_image(self):
        """check if the uploaded file is an image"""
        return self.upload and imghdr.what(self.upload.name)


class CompositeCalculation(JSONResponseMixin, View):
    """validate all qa tests in the request for the :model:`TestList` with id test_list_id"""

    def get_json_data(self, name):
        """return python data from GET json data"""

        json_string = self.request.body.decode("UTF-8")
        if not json_string:
            return

        try:
            return json.loads(json_string)[name]
        except (KeyError, ValueError):
            return

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
                exec(code, self.calculation_context)
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

    def set_composite_test_data(self):
        """retrieve calculation procs for all composite tests"""

        composite_ids = self.get_json_data("composite_ids")

        if composite_ids is None:
            self.composite_tests = {}
            return

        composite_tests = models.Test.objects.filter(
            pk__in=composite_ids
        ).values_list("slug", "calculation_procedure")

        self.composite_tests = dict(composite_tests)

    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""

        values = self.get_json_data("qavalues")
        meta_data = self.get_json_data("meta")

        for d in ("work_completed", "work_started",):
            try:
                meta_data[d] = dateutil.parser.parse(meta_data[d])
            except (KeyError, AttributeError):
                pass

        if values is None:
            self.calculation_context = {}
            return

        refs = self.get_json_data("refs")
        tols = self.get_json_data("tols")

        self.calculation_context = {
            "META": meta_data,
            "REFS": refs,
            "TOLS": tols,
        }

        self.calculation_context.update(DEFAULT_CALCULATION_CONTEXT)

        for slug, val in values.items():
            if slug not in self.composite_tests:
                self.calculation_context[slug] = val

    def set_dependencies(self):
        """figure out composite dependencies of composite tests"""

        self.dependencies = {}
        slugs = list(self.composite_tests.keys())
        for slug in slugs:
            tokens = utils.tokenize_composite_calc(self.composite_tests[slug])
            dependencies = [s for s in slugs if s in tokens and s != slug]
            self.dependencies[slug] = set(dependencies)

    def resolve_dependency_order(self):
        """
        Resolve calculation order dependencies using topological sort.

        This allows composite calculations to be calculated in the correct
        order for situations where you have composites that depend on
        other composites. For example, if A & B are both composite tests,
        but A is a function of B, then B must be calculated before A.
        Cyclical dependencies are also flagged.

        See http://code.activestate.com/recipes/577413-topological-sort/
        """

        #
        data = dict(self.dependencies)
        for k, v in list(data.items()):
            v.discard(k)  # Ignore self dependencies
        extra_items_in_deps = reduce(set.union, list(data.values())) - set(data.keys())
        data.update(dict((item, set()) for item in extra_items_in_deps))
        deps = []
        while True:
            ordered = set(item for item, dep in list(data.items()) if not dep)
            if not ordered:
                break
            deps.extend(list(sorted(ordered)))
            data = dict((item, (dep - ordered)) for item, dep in list(data.items()) if item not in ordered)

        self.calculation_order = deps
        self.cyclic_tests = list(data.keys())


class ChooseUnit(TemplateView):
    """View for selecting a unit to perform QA on"""

    template_name = "units/unittype_list.html"
    active_only = True

    def get_context_data(self, *args, **kwargs):
        """
        This is a view to present a list of :model:`units.Unit`'s grouped
        by :model:`units.UnitType` sorted according to the lowest unit
        number of its members.

        Only units which have :model:`qa.UnitTestCollection`'s that are
        visible to the user are included.
        """

        context = super(ChooseUnit, self).get_context_data(*args, **kwargs)

        groups = self.request.user.groups.all()
        q = models.UnitTestCollection.objects.by_visibility(groups)

        if self.active_only:
            q = q.filter(active=True)

        units_ordering = "unit__%s" % (settings.ORDER_UNITS_BY,)
        q = q.values("unit", "unit__type__name", "unit__name", "unit__number").order_by(units_ordering).distinct()

        unit_types = collections.defaultdict(list)
        for unit in q:
            unit_types[unit["unit__type__name"]].append(unit)

        ordered = sorted(list(unit_types.items()), key=lambda x: min([u[units_ordering] for u in x[1]]))

        context["unit_types"] = ordered

        return context


class PerformQA(PermissionRequiredMixin, CreateView):
    """
    This is the main view for users to complete a qa test list. i.e.
    for creating :model:`qa.TestListInstance` and :model:`qa.TestInstance`
    """

    permission_required = "qa.add_testlistinstance"
    raise_exception = True

    form_class = forms.CreateTestListInstanceForm
    model = models.TestListInstance

    def get_form_kwargs(self):
        k = super(PerformQA, self).get_form_kwargs()
        self.set_unit_test_collection()
        k['unit'] = self.unit_test_col.unit
        k['followup'] = self.request.GET.get('qaf', False)
        return k

    def set_test_lists(self):
        """
        Set the :model:`qa.TestList` and the day that are to be performed.
        The day is 0 for :model:`qa.TestList` or 0 - N-1 for
        :model:`qa.TestListCycle`'s (where N is number of lists in the cycle).
        """

        requested_day = self.get_requested_day_to_perform()
        self.actual_day, self.test_list = self.unit_test_col.get_list(requested_day)

        if self.test_list is None:
            raise Http404

        self.all_lists = [self.test_list] + list(self.test_list.sublists.order_by("name"))

    def set_all_tests(self):
        """Find all tests to be performed, including tests from sublists"""

        self.all_tests = []
        for test_list in self.all_lists:
            tests = test_list.tests.all().order_by("testlistmembership__order")
            self.all_tests.extend(tests)

    def set_unit_test_collection(self):
        """Set the requested :model:`qa.UnitTestCollection` to be performed."""

        self.unit_test_col = get_object_or_404(
            models.UnitTestCollection.objects.select_related(
                "unit", "frequency", "last_instance"
            ).filter(
                active=True,
                visible_to__in=self.request.user.groups.all(),
            ).distinct(),
            pk=self.kwargs["pk"]
        )

    def set_last_day(self):
        """Set the last day performed for the current :model:`UnitTestCollection`"""

        self.last_day = None

        if self.unit_test_col.last_instance:
            self.last_day = self.unit_test_col.last_instance.day + 1

    def template_unit_test_infos(self):
        """Convert :model:`qa.UnitTestInfo` into dicts for rendering in template"""

        template_utis = []
        for uti in self.unit_test_infos:
            template_utis.append({
                "id": uti.pk,
                "test": model_to_dict(uti.test),
                "reference": model_to_dict(uti.reference) if uti.reference else None,
                "tolerance": model_to_dict(uti.tolerance) if uti.tolerance else None,
            })

        return template_utis

    def set_unit_test_infos(self):
        """Find and order all :model:`qa.UniTestInfo` objects for tests to be performed"""

        utis = models.UnitTestInfo.objects.filter(
            unit=self.unit_test_col.unit,
            test__in=self.all_tests,
            active=True,
        ).select_related(
            "reference",
            "test__category",
            # "test__pk",
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
                # if this happens it usually indicates a bug somewhere. Please report.
                msg = "Do not treat! Please call physics.  Test '%s' is missing information for this unit " % test.name
                logger.error(msg + " Test=%d" % test.pk)
                messages.error(self.request, _(msg))

    def add_histories(self, forms):
        """paste historical values onto unit test infos (ugly)"""

        history, history_dates = self.unit_test_col.history()
        self.history_dates = history_dates
        for form in forms:
            for test, hist in history:
                if test == form.unit_test_info.test:
                    form.history = hist
                    break

    def get_test_status(self, form):
        """return default or user requested :model:`qa.TestInstanceStatus`"""

        try:
            status = models.TestInstanceStatus.objects.get(pk=form["status"].value())
            self.user_set_status = True
            return status
        except (KeyError, ValueError, models.TestInstanceStatus.DoesNotExist):
            self.user_set_status = False
            return models.TestInstanceStatus.objects.default()

    def form_valid(self, form):
        """
        TestListInstance form has validated, now check for validity of
        TestInstance formset, create all :model:`qa.TestInstance`s and do
        some bookeeping for the :model:`qa.TestListInstance`.
        """

        context = self.get_context_data()
        formset = context["formset"]

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
        wc = self.object.work_completed
        self.object.work_completed = wc if wc else self.object.modified

        self.object.reviewed = None if status.requires_review else self.object.modified
        self.object.reviewed_by = None if status.requires_review else self.request.user

        self.object.day = self.actual_day

        # save here so pk is set when saving test instances
        # and save below to get due deate set ocrrectly
        self.object.save()

        to_save = []

        for delta, ti_form in enumerate(formset):

            process_file_upload_form(ti_form, self.object)

            now = self.object.created + timezone.timedelta(milliseconds=delta)

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
                test_list_instance=self.object,
                work_started=self.object.work_started,
                work_completed=self.object.work_completed,
            )
            ti.calculate_pass_fail()
            if not self.user_set_status:
                ti.auto_review()

            to_save.append(ti)

        models.TestInstance.objects.bulk_create(to_save)

        # set due date to account for any non default statuses
        self.object.unit_test_collection.set_due_date()

        self.object.update_all_reviewed()

        service_event = form.cleaned_data.get('service_event', False)
        followup_id = form.cleaned_data.get('followup_id', False)

        print('-----sevice_event------')
        followup_id = self.request.GET.get('qaf', False)
        if service_event:

            if followup_id:
                followup = sl_models.QAFollowup.objects.get(pk=followup_id)
                followup.test_list_instance = self.object
            else:
                followup = sl_models.QAFollowup(
                    service_event=service_event,
                    unit_test_collection=self.object.unit_test_collection,
                    user_assigned_by=self.request.user,
                    datetime_assigned=timezone.now(),
                    test_list_instance=self.object
                )
            followup.save()

        if not self.object.in_progress:
            # TestListInstance & TestInstances have been successfully create, fire signal
            # to inform any listeners (e.g notifications.handlers.email_no_testlist_save)
            signals.testlist_complete.send(sender=self, instance=self.object, created=False)

        # let user know request succeeded and return to unit list
        messages.success(self.request, _("Successfully submitted %s " % self.object.test_list.name))

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(PerformQA, self).get_context_data(**kwargs)

        # context['service_event'] = self.request.GET.get('se', False)

        # explicity refresh session expiry to prevent situation where a session
        # expires in between the time a user requests a page and then submits the page
        # causing them to lose all the data they entered
        self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        if models.TestInstanceStatus.objects.default() is None:
            messages.error(self.request, "There must be at least one Test Status defined before performing a TestList")
            return context

        # setup our test list, tests, current day etc
        # self.set_unit_test_collection()
        self.set_test_lists()
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
            context['days'] = self.unit_test_col.tests_object.days_display()

        context["test_list"] = self.test_list
        context["unit_test_infos"] = json.dumps(self.template_unit_test_infos())
        context["unit_test_collection"] = self.unit_test_col
        context["contacts"] = list(Contact.objects.all().order_by("name"))
        print(self.object)
        print(self.unit_test_col.unit.id)
        qa_followup_id = self.request.GET.get('qaf', None)
        if qa_followup_id:
            qa_followup = sl_models.QAFollowup.objects.get(pk=qa_followup_id)
            context['se_statuses'] = {qa_followup.service_event.id: qa_followup.service_event.service_status.id}
        else:
            context['se_statuses'] = {}
        context['status_tag_colours'] = sl_models.ServiceEventStatus.get_colour_dict()

        print(context['status_tag_colours'])
        return context

    def get_requested_day_to_perform(self):
        """check GET to see if specific day requested by user"""
        try:
            # request comes in as 1 based day, convert to zero based
            day = int(self.request.GET.get("day")) - 1
        except (ValueError, TypeError, KeyError):
            day = None
        return day

    def get_success_url(self):
        """Redirect user to previous page they were on if possible"""

        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        kwargs = {
            "unit_number": self.unit_test_col.unit.number,
            "frequency": self.unit_test_col.frequency.slug if self.unit_test_col.frequency else "ad-hoc"
        }

        return reverse("qa_by_frequency_unit", kwargs=kwargs)


class EditTestListInstance(PermissionRequiredMixin, BaseEditTestListInstance):
    """
    View for users to edit an existing :model:`qa.TestListInstance` and
    its children :model:`qa.TestInstance`s.

    Note: Some of this code is duplicated in :view:`qa.views.perform.PerformQA`
    and the common parts may be able to be refactored into a mixin.
    """

    permission_required = "qa.change_testlistinstance"
    raise_exception = True

    form_class = forms.UpdateTestListInstanceForm
    formset_class = forms.UpdateTestInstanceFormSet

    def form_valid(self, form):

        self.form = form

        context = self.get_context_data(form=form)
        formset = context["formset"]

        if formset.is_valid():
            self.object = form.save(commit=False)

            status_pk = None
            if "status" in form.fields:
                status_pk = form["status"].value()
            self.set_status_object(status_pk)

            self.update_test_list_instance()

            for ti_form in formset:

                process_file_upload_form(ti_form, self.object)

                ti = ti_form.save(commit=False)
                self.update_test_instance(ti)

            self.object.unit_test_collection.set_due_date()

            self.object.update_all_reviewed()

            if not self.object.in_progress:
                signals.testlist_complete.send(sender=self, instance=self.object, created=False)

            # let user know request succeeded and return to unit list
            messages.success(self.request, _("Successfully submitted %s " % self.object.test_list.name))

            return HttpResponseRedirect(self.get_success_url())
        else:
            context["form"] = form
            return self.render_to_response(context)

    def update_test_list_instance(self):
        """do bookkeeping for :model:`qa.TestListInstance`"""

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

    def set_status_object(self, status_pk):

        try:
            self.status = models.TestInstanceStatus.objects.get(pk=status_pk)
            self.user_set_status = True
        except (models.TestInstanceStatus.DoesNotExist, ValueError):
            self.status = models.TestInstanceStatus.objects.default()
            self.user_set_status = False

    def update_test_instance(self, test_instance):
        """do bookkeeping for :model:`qa.TestInstance`"""

        ti = test_instance
        ti.status = self.status
        ti.modified_by = self.request.user
        ti.work_started = self.object.work_started
        ti.work_completed = self.object.work_completed

        try:
            ti.calculate_pass_fail()
            if not self.user_set_status:
                ti.auto_review()

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

    def get_context_data(self, **kwargs):

        context = super(EditTestListInstance, self).get_context_data(**kwargs)
        self.unit_test_infos = [f.instance.unit_test_info for f in context["formset"]]
        context["unit_test_infos"] = json.dumps(self.template_unit_test_infos())

        qa_followup_id = self.request.GET.get('qaf', None)
        if qa_followup_id:
            qa_followup = sl_models.QAFollowup.objects.get(pk=qa_followup_id)
            context['se_statuses'] = {qa_followup.service_event.id: qa_followup.service_event.service_status.id}
        else:
            context['se_statuses'] = {}
        context['status_tag_colours'] = sl_models.ServiceEventStatus.get_colour_dict()

        print(context['status_tag_colours'])
        return context


class ContinueTestListInstance(EditTestListInstance):
    """
    View for continuing a :model:`qa.TestListInstance` that has previously
    been marked as in progress.
    """

    permission_required = "qa.add_testlistinstance"
    raise_exception = True


class InProgress(TestListInstances):
    """
    View for choosing an existing from the :model:`qa.TestListInstance`s
    which are marked as being in progress.
    """

    def get_queryset(self):
        return models.TestListInstance.objects.in_progress()

    def get_icon(self):
        return 'fa-play'

    def get_page_title(self):
        return "In Progress Test Lists"


class FrequencyList(UTCList):
    """List :model:`qa.UnitTestCollection`s for requested :model:`qa.Frequency`s"""

    def get_queryset(self):
        """filter queryset by frequency"""

        qs = super(FrequencyList, self).get_queryset()

        freqs = self.kwargs["frequency"].split("/")
        self.frequencies = models.Frequency.objects.filter(slug__in=freqs)

        q = Q(frequency__in=self.frequencies)
        if "ad-hoc" in freqs:
            q |= Q(frequency=None)

        return qs.filter(q).distinct()

    def get_page_title(self):
        return ",".join([x.name if x else "ad-hoc" for x in self.frequencies]) + " Test Lists"


class UnitFrequencyList(FrequencyList):
    """
    List :model:`qa.UnitTestCollection`s for requested :model:`unit.Unit`s
    and :model:`qa.Frequency`s.
    """

    def get_queryset(self):
        """filter queryset by Unit"""

        qs = super(UnitFrequencyList, self).get_queryset()
        self.units = Unit.objects.filter(number__in=self.kwargs["unit_number"].split("/"))
        return qs.filter(unit__in=self.units)

    def get_page_title(self):
        title = ", ".join([x.name for x in self.units])
        title += " " + ", ".join([x.name if x else "ad-hoc" for x in self.frequencies]) + " Test Lists"
        return title


class UnitList(UTCList):
    """ List :model:`qa.UnitTestCollection`s for requested :model:`unit.Unit`s """

    def get_queryset(self):
        """filter queryset by frequency"""
        qs = super(UnitList, self).get_queryset()
        self.units = Unit.objects.filter(
            number__in=self.kwargs["unit_number"].split("/")
        )
        return qs.filter(unit__in=self.units)

    def get_page_title(self):
        title = ", ".join([x.name for x in self.units]) + " Test Lists"
        return title
