import collections
import json
import math
import os
import traceback
from functools import reduce

import dateutil
import dicom
import matplotlib
import matplotlib.pyplot as plt
import numpy
import scipy
from braces.views import JSONResponseMixin, PermissionRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, TemplateView, View
from django_comments.models import Comment

from qatrack.attachments.models import Attachment
from qatrack.attachments.utils import imsave, to_bytes
from qatrack.contacts.models import Contact
from qatrack.service_log import models as sl_models
from qatrack.units.models import Site, Unit

from . import forms
from .. import models, signals, utils
from .base import BaseEditTestListInstance, TestListInstances, UTCList, logger

DEFAULT_CALCULATION_CONTEXT = {
    "dicom": dicom,
    "math": math,
    "numpy": numpy,
    "matplotlib": matplotlib,
    "scipy": scipy,
}


def process_procedure(procedure):
    """
    Cleans and sets new style division for calculations procedures. Used by
    both the :view:`qa.perform.Upload` &
    :view:`qa.perform.CompositeCalculation` views.

    """
    return "\n".join(["from __future__ import division", procedure, "\n"]).replace('\r', '\n')


def set_attachment_owners(test_list_instance, attachments):

    tis = test_list_instance.testinstance_set.select_related("unit_test_info")
    for uti_id, attachment in attachments:
        for ti in tis:
            if ti.unit_test_info.pk == uti_id:
                attachment.testinstance = ti
                attachment.save()


def attachment_info(attachment):
    return {
        'attachment_id': attachment.id,
        'name': os.path.basename(attachment.attachment.name),
        'size': filesizeformat(attachment.attachment.size),
        'url': attachment.attachment.url,
        'is_image': attachment.is_image,
    }


class CompositeUtils:

    def __init__(self, user, context, comments):
        self.context = context
        self.context['__user_attached__'] = []
        self.user = user
        self.comments = comments

    def set_comment(self, comment):
        self.context["__comment__"] = comment

    def get_comment(self, slug):
        return self.comments.get(slug, "")

    def write_file(self, fname, obj):
        fname = os.path.basename(fname)
        data = imsave(obj, fname)
        if data is None:
            data = to_bytes(obj, fname)

        f = ContentFile(data, fname)

        attachment = Attachment(
            attachment=f,
            comment=_("Composite created file"),
            created_by=self.user,
        )
        attachment.save()

        self.context["__user_attached__"].append(attachment_info(attachment))


def get_context_refs_tols(unit, tests):

    utis = models.UnitTestInfo.objects.filter(
        unit=unit,
        test_id__in=tests.values_list("id"),
        active=True,
    ).select_related("reference", "test", "tolerance",).values(
        "test__slug",
        "reference__value",
        "tolerance__type",
        "tolerance__mc_tol_choices",
        "tolerance__mc_pass_choices",
        "tolerance__act_high",
        "tolerance__act_low",
        "tolerance__tol_high",
        "tolerance__tol_low",
    )
    refs = {}
    tols = {}
    tol_keys = ["act_high", "act_low", "tol_high", "tol_low", "mc_pass_choices", "mc_tol_choices", "type"]
    for uti in utis:
        slug = uti["test__slug"]
        refs[slug] = uti['reference__value']
        tols[slug] = {k: uti["tolerance__%s" % k] for k in tol_keys}

    return refs, tols


class Upload(JSONResponseMixin, View):
    """View for handling AJAX upload requests when performing QA"""

    # use html for IE8's sake :(
    content_type = "text/html"

    def post(self, *args, **kwargs):
        """process file, apply calculation procedure and return results"""

        try:
            self.test_list = models.TestList.objects.get(pk=self.get_json_data("test_list_id"))
            self.all_tests = self.test_list.all_tests()
        except (models.TestList.DoesNotExist):
            return self.render_json_response({"success": False, "errors": ["Invalid or missing test_list_id"]})

        try:
            self.unit = Unit.objects.get(pk=self.get_json_data("unit_id"))
        except (Unit.DoesNotExist):
            return self.render_json_response({"success": False, "errors": ["Invalid or missing unit_id"]})

        try:
            if self.request.POST.get('attachment_id'):
                self.reprocess()
            else:
                self.handle_upload()

            resp = self.run_calc()
        except Exception:
            msg = traceback.format_exc()
            results = {
                'success': False,
                'errors': [msg],
                "result": None,
                "user_attached": [],
            }
            resp = self.render_json_response(results)
        """
        At the end of any view which may use mpl.pyplot to generate a plot
        we need to clean the figure, to attempt to  prevent any crosstalk
        between plots.

        Generally people should use the OO interface to MPL rather than
        pyplot, because pyplot is not threadsafe.
        """
        plt.clf()
        return resp

    def reprocess(self):
        self.attach_id = self.request.POST.get("attachment_id")
        try:
            self.attachment = Attachment.objects.get(pk=self.attach_id)
        except Attachment.DoesNotExist:
            self.attachment = None

    def run_calc(self):

        self.set_calculation_context()

        results = {
            'attachment_id': self.attachment.id,
            'attachment': attachment_info(self.attachment),
            'success': False,
            'errors': [],
            "result": None,
            "comment": "",
            "user_attached": [],
        }

        if self.attachment is None:
            results["errors"] = ["Original file not found. Please re-upload."]
            return self.render_json_response(results)

        try:
            test = models.Test.objects.get(pk=self.request.POST.get("test_id"))
            code = compile(process_procedure(test.calculation_procedure), "__QAT+COMP_%s.py" % test.slug, "exec")
            exec(code, self.calculation_context)
            key = "result" if "result" in self.calculation_context else test.slug
            results["result"] = self.calculation_context[key]
            results["success"] = True
            results["user_attached"] = list(self.calculation_context.get("__user_attached__", []))
            results["comment"] = self.calculation_context.get("__comment__")
        except models.Test.DoesNotExist:
            results["errors"].append("Test with that ID does not exist")
        except Exception:
            msg = traceback.format_exc().split("__QAT+COMP_")[-1].replace("<module>", "Test: %s" % test.name)
            results["errors"].append("Invalid Test Procedure: %s" % msg)

        return self.render_json_response(results)

    def handle_upload(self):
        """read incoming file and save tmp file to disk ready for processing"""

        comment = "Uploaded %s by %s" % (timezone.now(), self.request.user.username)
        f = self.request.FILES.get('upload')
        self.attachment = Attachment.objects.create(
            attachment=f,
            label=f.name,
            comment=comment,
            created_by=self.request.user,
        )

    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""

        self.calculation_context = {}

        meta_data = self.get_json_data("meta")
        refs, tols = get_context_refs_tols(self.unit, self.all_tests)

        for d in ("work_completed", "work_started"):
            try:
                meta_data[d] = dateutil.parser.parse(meta_data[d])
            except (KeyError, AttributeError, TypeError):
                pass

        comments = self.get_json_data("comments")
        self.calculation_context.update({
            "FILE": open(self.attachment.attachment.path, "r"),
            "BIN_FILE": self.attachment.attachment,
            "META": meta_data,
            "REFS": refs,
            "TOLS": tols,
            "UTILS": CompositeUtils(self.request, self.calculation_context, comments),
        })
        self.calculation_context.update(DEFAULT_CALCULATION_CONTEXT)

    def get_json_data(self, name):
        """return python data from GET json data"""
        json_string = self.request.POST.get(name)
        if not json_string:
            return

        try:
            return json.loads(json_string)
        except (KeyError, ValueError):
            return


class CompositePerformer:

    def __init__(self, user, data):
        self.user = user
        self.data = data

    def calculate(self):
        """calculate and return all composite values"""

        try:
            self.test_list = models.TestList.objects.get(pk=self.data["test_list_id"])
            self.all_tests = self.test_list.all_tests()
        except (KeyError, models.TestList.DoesNotExist):
            return {"success": False, "errors": ["Invalid or missing test_list_id"]}

        try:
            self.unit = Unit.objects.get(pk=self.data["unit_id"])
        except (KeyError, Unit.DoesNotExist):
            return {"success": False, "errors": ["Invalid or missing unit_id"]}

        self.set_composite_test_data()
        if not self.composite_tests:
            return {"success": False, "errors": ["No Valid Composite ID's"]}

        self.set_calculation_context()
        if not self.calculation_context or list(self.calculation_context.keys()) == ["write_file"]:
            return {"success": False, "errors": ["Invalid QA Values"]}

        self.set_dependencies()
        self.resolve_dependency_order()

        results = {}

        for slug in self.cyclic_tests:
            results[slug] = {'value': None, 'error': "Cyclic test dependency"}

        for slug in self.calculation_order:
            raw_procedure = self.composite_tests[slug]
            procedure = process_procedure(raw_procedure)
            try:
                code = compile(procedure, "__QAT+COMP_%s" % slug, "exec")
                exec(code, self.calculation_context)
                key = "result" if "result" in self.calculation_context else slug
                result = self.calculation_context[key]

                results[slug] = {
                    'value': result,
                    'error': None,
                    'user_attached': list(self.calculation_context.get("__user_attached__", [])),
                    'comment': self.calculation_context.get("__comment__"),
                }
                self.calculation_context[slug] = result
            except Exception:
                msg = traceback.format_exc().split("__QAT+COMP_")[-1].replace("<module>", slug)
                results[slug] = {
                    'value': None,
                    'error': "Invalid Test Procedure: %s" % msg,
                    'comment': "",
                    'user_attached': [],
                }
            finally:
                # clean up calculation context for next test
                to_clean = ['result'] + [k for k in self.calculation_context.keys() if k not in self.context_keys]
                to_clean = set([k for k in to_clean if k in self.calculation_context])
                for k in to_clean:
                    del self.calculation_context[k]

                del self.calculation_context['__user_attached__'][:]

        return {"success": True, "errors": [], "results": results}

    def set_composite_test_data(self):
        """retrieve calculation procs for all composite tests"""

        composite_tests = self.all_tests.filter(
            type__in=models.COMPOSITE_TYPES,
        ).values_list("slug", "calculation_procedure")

        self.composite_tests = dict(composite_tests)

    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""

        self.calculation_context = {}
        values = self.data.get("tests")
        meta_data = self.data.get("meta")

        for d in ("work_completed", "work_started"):
            try:
                meta_data[d] = dateutil.parser.parse(meta_data[d])
            except (TypeError, KeyError, AttributeError):
                pass

        if values is None:
            return

        refs, tols = get_context_refs_tols(self.unit, self.all_tests)

        comments = self.data.get("comments", {})
        self.calculation_context.update({
            "META": meta_data,
            "REFS": refs,
            "TOLS": tols,
            "UTILS": CompositeUtils(self.user, self.calculation_context, comments),
        })

        self.calculation_context.update(DEFAULT_CALCULATION_CONTEXT)

        self.context_keys = list(self.calculation_context.keys())

        for slug, val in values.items():
            self.context_keys.append(slug)
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


class CompositeCalculation(JSONResponseMixin, View):
    """validate all qa tests in the request for the :model:`TestList` with id test_list_id"""

    def post(self, *args, **kwargs):
        """calculate and return all composite values"""

        json_string = self.request.body.decode("UTF-8")
        if not json_string:
            data = {}
        try:
            data = json.loads(json_string)
        except (ValueError):
            data = {}

        result = CompositePerformer(self.request.user, data).calculate()
        return self.render_json_response(result)


class ChooseUnit(TemplateView):
    """View for selecting a unit to perform QA on"""

    template_name = 'units/unittype_list.html'
    active_only = True
    split_sites = True

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
            q = q.filter(active=True, unit__active=True)

        units_ordering = 'unit__%s' % (settings.ORDER_UNITS_BY,)

        if Site.objects.all().exists() and self.split_sites:

            unit_site_types = {}
            for s in Site.objects.all():
                unit_site_types[s.name] = collections.defaultdict(list)
            if q.filter(unit__site__isnull=True).exists():
                unit_site_types['zzzNonezzz'] = collections.defaultdict(list)

            q = q.values(
                'unit',
                'unit__type__name',
                'unit__name',
                'unit__number',
                'unit__id',
                'unit__site__name',
            ).order_by(units_ordering).distinct()

            freq_qs = models.Frequency.objects.prefetch_related('unittestcollections__unit').all()

            for unit in q:
                unit['frequencies'] = freq_qs.filter(
                    unittestcollections__unit_id=unit['unit__id'],
                ).distinct().values(
                    'slug',
                    'name',
                )

                if unit['unit__site__name']:
                    unit_site_types[unit['unit__site__name']][unit['unit__type__name']].append(unit)
                else:
                    unit_site_types['zzzNonezzz'][unit['unit__type__name']].append(unit)

            ordered = {}
            for s in unit_site_types:
                ordered[s] = sorted(
                    list(unit_site_types[s].items()), key=lambda x: min([u[units_ordering] for u in x[1]])
                )

            ordered = collections.OrderedDict(sorted(ordered.items(), key=lambda s: s[0]))

            context['split_sites'] = True

            split_by = 12 / len(ordered)
            if split_by < 3:
                split_by = 3
            context['split_by'] = int(split_by)

        else:
            q = q.values('unit', 'unit__type__name', 'unit__name', 'unit__number',
                         'unit__id').order_by(units_ordering).distinct()
            freq_qs = models.Frequency.objects.prefetch_related('unittestcollections__unit').all()

            unit_types = collections.defaultdict(list)
            for unit in q:
                unit['frequencies'] = freq_qs.filter(unittestcollections__unit_id=unit['unit__id']).distinct().values(
                    'slug', 'name'
                )
                unit_types[unit["unit__type__name"]].append(unit)

            ordered = sorted(list(unit_types.items()), key=lambda x: min([u[units_ordering] for u in x[1]]))
            context['split_sites'] = False

        context['unit_types'] = ordered

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
        k['rtsqa'] = self.request.GET.get('rtsqa', False)
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

    def set_all_tests(self):
        """Find all tests to be performed, including tests from sublists"""
        self.all_tests = self.test_list.ordered_tests()

    def set_unit_test_collection(self):
        """Set the requested :model:`qa.UnitTestCollection` to be performed."""

        self.unit_test_col = get_object_or_404(
            models.UnitTestCollection.objects.select_related(
                "unit",
                "frequency",
                "last_instance",
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

        in_progress = form.cleaned_data['in_progress']
        for f in formset:
            f.in_progress = in_progress

        if not formset.is_valid():
            context["form"] = form
            return self.render_to_response(context)

        status = self.get_test_status(form)

        self.object = form.save(commit=False)
        self.object.due_date = self.unit_test_col.due_date
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

        self.create_tli_attachments()

        to_save = []

        attachments = []

        if form.cleaned_data['comment']:
            comment = Comment(
                submit_date=timezone.now(),
                user=self.request.user,
                content_object=self.object,
                comment=form.cleaned_data['comment'],
                site=get_current_site(self.request)
            )
            comment.save()

        for delta, ti_form in enumerate(formset):

            now = self.object.created + timezone.timedelta(milliseconds=delta)

            attachments.extend(ti_form.attachments_to_process)

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

        set_attachment_owners(self.object, attachments)

        # set due date to account for any non default statuses
        self.object.unit_test_collection.set_due_date()

        # service_events = form.cleaned_data.get('service_events', False)
        rtsqa_id = form.cleaned_data['rtsqa_id']

        # is there an existing rtsqa being linked?
        if rtsqa_id:
            rtsqa = sl_models.ReturnToServiceQA.objects.get(pk=rtsqa_id)
            rtsqa.test_list_instance = self.object
            rtsqa.save()

            # If tli needs review, update 'Unreviewed RTS QA' counter
            if not self.object.all_reviewed:
                cache.delete(settings.CACHE_RTS_QA_COUNT)

        changed_se = self.object.update_all_reviewed()

        if len(changed_se) > 0:
            messages.add_message(
                request=self.request,
                level=messages.INFO,
                message='Changed status of service event(s) %s to "%s".' %
                (', '.join(str(x) for x in changed_se), sl_models.ServiceEventStatus.get_default().name)
            )

        if not self.object.in_progress:
            # TestListInstance & TestInstances have been successfully create, fire signal
            # to inform any listeners (e.g notifications.handlers.email_no_testlist_save)
            try:
                signals.testlist_complete.send(sender=self, instance=self.object, created=False)
            except:
                messages.add_message(
                    request=self.request, message='Error sending notification email.', level=messages.ERROR
                )

        # let user know request succeeded and return to unit list
        messages.success(self.request, _("Successfully submitted %s " % self.object.test_list.name))

        return HttpResponseRedirect(self.get_success_url())

    def create_tli_attachments(self):
        for idx, f in enumerate(self.request.FILES.getlist('tli-attachments')):
            Attachment.objects.create(
                attachment=f,
                comment="Uploaded %s by %s" % (timezone.now(), self.request.user.username),
                label=f.name,
                testlistinstance=self.object,
                created_by=self.request.user
            )

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
            formset = forms.CreateTestInstanceFormSet(
                self.request.POST, self.request.FILES, unit_test_infos=self.unit_test_infos, user=self.request.user
            )
        else:
            formset = forms.CreateTestInstanceFormSet(unit_test_infos=self.unit_test_infos, user=self.request.user)

        self.add_histories(formset.forms)

        context["formset"] = formset
        context["history_dates"] = self.history_dates
        context['categories'] = set([x.test.category for x in self.unit_test_infos])
        context['current_day'] = self.actual_day + 1
        context["last_instance"] = self.unit_test_col.last_instance
        context['last_day'] = self.last_day
        context['borders'] = self.test_list.sublist_borders(self.all_tests)

        ndays = len(self.unit_test_col.tests_object)
        if ndays > 1:
            context['days'] = self.unit_test_col.tests_object.days_display()

        in_progress = models.TestListInstance.objects.in_progress().filter(
            unit_test_collection=self.unit_test_col, test_list=self.test_list
        )
        context["test_list"] = self.test_list
        context["in_progress"] = in_progress
        context["unit_test_infos"] = json.dumps(self.template_unit_test_infos())
        context["unit_test_collection"] = self.unit_test_col
        context["contacts"] = list(Contact.objects.all().order_by("name"))

        rtsqa_id = self.request.GET.get('rtsqa', None)
        if rtsqa_id:
            rtsqa = sl_models.ReturnToServiceQA.objects.get(pk=rtsqa_id)
            context['se_statuses'] = {rtsqa.service_event.id: rtsqa.service_event.service_status.id}
            context['rtsqa_id'] = rtsqa_id
            context['rtsqa_for_se'] = rtsqa.service_event

        context['attachments'] = (
            context['test_list'].attachment_set.all() |
            self.unit_test_col.tests_object.attachment_set.all()
        )

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

                ti = ti_form.save(commit=False)

                self.update_test_instance(ti)

                ti.attachment_set.clear()

                for uti_pk, attachment in ti_form.attachments_to_process:
                    attachment.testinstance = ti
                    attachment.save()

            self.object.unit_test_collection.set_due_date()

            # # service_events = form.cleaned_data.get('service_events', False)
            # rtsqa_id = self.request.GET.get('rtsqa', False)
            #
            # if rtsqa_id:
            #     rtsqa = sl_models.ReturnToServiceQA.objects.get(pk=rtsqa_id)
            #     rtsqa.test_list_instance = self.object
            #     rtsqa.save()

            changed_se = self.object.update_all_reviewed()

            if len(changed_se) > 0:
                messages.add_message(
                    request=self.request,
                    level=messages.INFO,
                    message='Changed status of service event(s) %s to "%s".' %
                    (', '.join(str(x) for x in changed_se), sl_models.ServiceEventStatus.get_default().name)
                )

            if not self.object.in_progress:
                try:
                    signals.testlist_complete.send(sender=self, instance=self.object, created=False)
                except:
                    messages.add_message(
                        request=self.request,
                        message='Error sending notification email.',
                        level=messages.ERROR,
                    )

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

        if self.request.FILES:
            self.update_attachments()

    def update_attachments(self):
        for attach in self.object.attachment_set.all():
            attach.delete()

        for idx, f in enumerate(self.request.FILES.getlist('tli-attachments')):
            Attachment.objects.create(
                attachment=f,
                comment="Uploaded %s by %s" % (timezone.now(), self.request.user.username),
                label=f.name,
                testlistinstance=self.object,
                created_by=self.request.user
            )

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
        uti_pks = [f.instance.unit_test_info.pk for f in context["formset"]]
        utis = models.UnitTestInfo.objects.filter(pk__in=uti_pks).select_related(
            "reference",
            "tolerance",
            "unit",
            "test__category",
        ).prefetch_related(
            "test__attachment_set",
        )
        self.unit_test_infos = list(sorted(utis, key=lambda x: uti_pks.index(x.pk)))

        context["unit_test_infos"] = json.dumps(self.template_unit_test_infos())

        context['attachments'] = context['test_list'].attachment_set.all(
        ) | self.object.unit_test_collection.tests_object.attachment_set.all()

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
        self.units = Unit.objects.filter(number__in=self.kwargs["unit_number"].split("/"))
        return qs.filter(unit__in=self.units)

    def get_page_title(self):
        title = ", ".join([x.name for x in self.units]) + " Test Lists"
        return title
