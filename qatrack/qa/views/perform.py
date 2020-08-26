import collections
from functools import reduce
import json
import math
import os
import traceback

from braces.views import JSONResponseMixin, PermissionRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, QuerySet
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import CreateView, TemplateView, View
from django_comments.models import Comment
import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy
import pydicom as dicom
import scipy

from qatrack.attachments.models import Attachment
from qatrack.attachments.utils import imsave, to_bytes
from qatrack.contacts.models import Contact
from qatrack.qa.trees import BootstrapCategoryTree, BootstrapFrequencyTree
from qatrack.qatrack_core.serializers import QATrackJSONEncoder
from qatrack.qatrack_core.utils import (
    format_datetime,
    parse_date,
    parse_datetime,
)
from qatrack.service_log import models as sl_models
from qatrack.units.models import Site, Unit

from . import forms
from .. import models, signals, utils
from .base import BaseEditTestListInstance, TestListInstances, UTCList, logger

DEFAULT_CALCULATION_CONTEXT = {
    "dicom": dicom,
    "pydicom": dicom,
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
    return "\n".join([procedure, "\n"]).replace('\r', '\n')


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

    def __init__(self, user, unit, test_list, meta, context, comments, skips):
        self.context = context
        self.context['__user_attached__'] = []
        self.user = user
        self.unit = unit
        self.meta = meta
        self.test_list = test_list
        self.comments = comments
        self.skips = skips

    def set_comment(self, comment):
        self.context["__comment__"] = comment

    def get_comment(self, slug):
        return self.comments.get(slug, "")

    def set_skip(self, slug, skip):
        self.skips[slug] = skip

    def get_skip(self, slug):
        return self.skips.get(slug, False)

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

    def previous_test_list_instance(self, include_in_progress=False):
        before = self.meta.get("work_started", self.meta.get("work_completed")) or timezone.now()
        qs = models.TestListInstance.objects.filter(
            test_list=self.test_list,
            unit_test_collection__unit=self.unit,
            work_completed__lt=before,
        )
        if not include_in_progress:
            qs = qs.exclude(in_progress=True)

        try:
            return qs.latest("work_completed")
        except models.TestListInstance.DoesNotExist:
            return None

    def previous_test_instance(self, test=None, same_list_only=True, include_in_progress=False, exclude_skipped=True):
        try:
            slug = test.slug
        except AttributeError:
            slug = test

        before = self.meta.get("work_started", self.meta.get("work_completed")) or timezone.now()
        qs = models.TestInstance.objects.filter(
            unit_test_info__test__slug=slug,
            unit_test_info__unit=self.unit,
            work_completed__lt=before,
        )
        if same_list_only:
            qs = qs.filter(test_list_instance__test_list=self.test_list)
        if not include_in_progress:
            qs = qs.exclude(test_list_instance__in_progress=True)
        if exclude_skipped:
            qs = qs.exclude(skipped=True)

        try:
            return qs.latest("work_completed")
        except models.TestInstance.DoesNotExist:
            return None

    def get_test_instance(
        self,
        test_id=None,
        test_name=None,
        test_list_id=None,
        include_in_progress=False,
        exclude_skipped=True,
        include_invalid=False,
        unit_number=None,
        start_window=None,
        end_window=None,
    ):

        qs = models.TestInstance.objects.all()

        if test_id is not None:
            qs = qs.filter(unit_test_info__test_id=test_id)

        if test_name is not None:
            qs = qs.filter(unit_test_info__test__name=test_name)

        if start_window is not None:
            qs = qs.filter(test_list_instance__work_completed__gte=start_window)

        if end_window is None:
            end_window = self.meta.get("work_started", self.meta.get("work_completed")) or timezone.now()

        qs = qs.filter(test_list_instance__work_completed__lte=end_window)

        if test_list_id:
            qs = qs.filter(test_list_instance__test_list_id=test_list_id)

        if not include_in_progress:
            qs = qs.filter(test_list_instance__in_progress=False)

        if exclude_skipped:
            qs = qs.filter(skipped=False)

        if not include_invalid:
            qs = qs.filter(status__valid=True)

        if unit_number is None:
            unit_number = self.unit.number

        qs = qs.filter(unit_test_info__unit__number=unit_number)

        try:
            return qs.latest("work_completed")
        except models.TestInstance.DoesNotExist:
            return None

    def get_figure(self):
        fig = Figure()
        FigureCanvasAgg(fig)
        return fig


def get_context_refs_tols(unit, tests):

    if isinstance(tests, QuerySet):
        ids = tests.values_list("id")
    else:
        ids = [x.id for x in tests]

    utis = models.UnitTestInfo.objects.filter(
        unit=unit,
        test_id__in=ids,
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


class UploadHandler:

    def __init__(self, user, data, fp):
        self.user = user
        self.data = data
        self.file = fp

    def process(self):
        """process file, apply calculation procedure and return results"""

        try:
            self.test_list = models.TestList.objects.get(pk=self.data["test_list_id"])
            self.all_tests = self.test_list.all_tests()
        except (KeyError, models.TestList.DoesNotExist):
            return {"success": False, "errors": ["Invalid or missing test_list_id"]}

        try:
            self.unit = Unit.objects.get(pk=self.data["unit_id"])
        except (KeyError, Unit.DoesNotExist):
            return {"success": False, "errors": ["Invalid or missing unit_id"]}

        try:
            if self.data.get('attachment_id'):
                self.reprocess()
            else:
                self.handle_upload()

            results = self.run_calc()
        except Exception:
            msg = traceback.format_exc(limit=5, chain=True)
            results = {
                'success': False,
                'errors': [msg],
                "result": None,
                "user_attached": [],
            }

        return results

    def reprocess(self):
        self.attach_id = self.data.get("attachment_id")
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
            results["errors"] = [_("Original file not found. Please re-upload.")]
            return results

        try:
            test = models.Test.objects.get(pk=self.data.get("test_id"))
            code = compile(process_procedure(test.calculation_procedure), "__QAT+COMP_%s.py" % test.slug, "exec")
            exec(code, self.calculation_context)
            key = "result" if "result" in self.calculation_context else test.slug
            results["result"] = self.calculation_context[key]
            results["success"] = True
            results["user_attached"] = list(self.calculation_context.get("__user_attached__", []))
            results["comment"] = self.calculation_context.get("__comment__")
            results["skips"] = self.calculation_context['UTILS'].skips
        except models.Test.DoesNotExist:
            results["errors"].append(_("Test with that ID does not exist"))
        except Exception:
            msg = traceback.format_exc(
                limit=5, chain=True
            ).split("__QAT+COMP_")[-1].replace("<module>", _("Test: %(test_name)s") % {'test_name': test.name})
            results["errors"].append(_("Invalid Test Procedure: %(traceback)s") % {'traceback': msg})

        return results

    def handle_upload(self):
        """read incoming file and save tmp file to disk ready for processing"""

        comment = _("Uploaded %(current_datetime)s by %(username)s") % {
            'current_datetime': timezone.now(),
            'username': self.user.username
        }
        self.attachment = Attachment.objects.create(
            attachment=self.file,
            label=self.file.name,
            comment=comment,
            created_by=self.user,
        )

    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""

        self.calculation_context = {}

        meta_data = self.data["meta"]
        refs, tols = get_context_refs_tols(self.unit, self.all_tests)

        tz = timezone.get_current_timezone()
        for d in ("work_completed", "work_started"):
            try:
                meta_data[d] = tz.localize(parse_datetime(meta_data[d]))
            except (TypeError, KeyError, AttributeError):
                pass

        comments = self.data["comments"]
        skips = self.data.get("skips", {})
        self.calculation_context.update({
            "FILE": open(self.attachment.attachment.path, "r"),
            "BIN_FILE": self.attachment.attachment,
            "META": meta_data,
            "REFS": refs,
            "TOLS": tols,
            "UTILS": CompositeUtils(
                self.user,
                self.unit,
                self.test_list,
                meta_data,
                self.calculation_context,
                comments,
                skips,
            ),
        })
        self.calculation_context.update(DEFAULT_CALCULATION_CONTEXT)


class Upload(JSONResponseMixin, View):
    """View for handling AJAX upload requests when performing QC"""

    # use html for IE8's sake :(
    content_type = "text/html"
    json_encoder_class = QATrackJSONEncoder

    def post(self, *args, **kwargs):
        """process file, apply calculation procedure and return results"""

        try:
            self.test_list = models.TestList.objects.get(pk=self.get_json_data("test_list_id"))
            self.all_tests = self.test_list.all_tests()
        except (models.TestList.DoesNotExist):
            return self.render_json_response({"success": False, "errors": [_("Invalid or missing test_list_id")]})

        try:
            self.unit = Unit.objects.get(pk=self.get_json_data("unit_id"))
        except (Unit.DoesNotExist):
            return self.render_json_response({"success": False, "errors": [_("Invalid or missing unit_id")]})

        try:
            if self.request.POST.get('attachment_id'):
                self.reprocess()
            else:
                self.handle_upload()

            resp = self.run_calc()
        except Exception:
            msg = traceback.format_exc(limit=5, chain=True)
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
            results["errors"] = [_("Original file not found. Please re-upload.")]
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
            results["skips"] = self.calculation_context['UTILS'].skips
        except models.Test.DoesNotExist:
            results["errors"].append(_("Test with that ID does not exist"))
        except Exception:
            msg = traceback.format_exc(
                limit=5, chain=True
            ).split("__QAT+COMP_")[-1].replace("<module>", _("Test: %(test_name)s") % {'test_name': test.name})
            results["errors"].append(_("Invalid Test Procedure: %(traceback)s") % {'traceback': msg})

        return self.render_json_response(results)

    def handle_upload(self):
        """read incoming file and save tmp file to disk ready for processing"""

        comment = _("Uploaded %(current_datetime)s by %(username)s") % {
            'current_datetime': format_datetime(timezone.now()),
            'username': self.request.user.username
        }
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

        tz = timezone.get_current_timezone()
        for d in ("work_completed", "work_started"):
            try:
                meta_data[d] = tz.localize(parse_datetime(meta_data[d]))
            except (KeyError, AttributeError, TypeError):
                pass

        comments = self.get_json_data("comments")
        skips = self.get_json_data("skips")

        try:
            f = open(self.attachment.attachment.path, "r")
        except NotImplementedError:
            self.attachment.attachment.open("r")
            f = self.attachment.attachment

        self.calculation_context.update({
            "FILE": f,
            "BIN_FILE": self.attachment.attachment,
            "META": meta_data,
            "REFS": refs,
            "TOLS": tols,
            "UTILS": CompositeUtils(
                self.request.user,
                self.unit,
                self.test_list,
                meta_data,
                self.calculation_context,
                comments,
                skips,
            ),
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
        self.defaults = data.get('defaults')

    def calculate(self):
        """calculate and return all composite values"""

        try:
            self.test_list = models.TestList.objects.get(pk=self.data["test_list_id"])
            self.all_tests = list(self.test_list.all_tests())
        except (KeyError, models.TestList.DoesNotExist):
            return {"success": False, "errors": [_("Invalid or missing test_list_id")]}

        try:
            self.unit = Unit.objects.get(pk=self.data["unit_id"])
        except (KeyError, Unit.DoesNotExist):
            return {"success": False, "errors": [_("Invalid or missing unit_id")]}

        self.set_test_types()
        self.set_formatters()

        self.set_composite_test_data()
        if not self.composite_tests:
            return {"success": False, "errors": [_("No Valid Composite ID's")]}

        self.set_calculation_context()
        if not self.calculation_context or list(self.calculation_context.keys()) == ["write_file"]:
            return {"success": False, "errors": [_("Invalid QC Values")]}

        self.set_dependencies()
        self.resolve_dependency_order()

        results = {}

        for slug in self.cyclic_tests:
            results[slug] = {
                'value': None,
                'error': _("Cyclic test dependency"),
            }

        for slug in self.calculation_order:
            raw_procedure = self.composite_tests[slug]
            procedure = process_procedure(raw_procedure)
            tb_limit = 5
            try:
                code = compile(procedure, "__QAT+COMP_%s" % slug, "exec")
                exec(code, self.calculation_context)
                key = "result" if "result" in self.calculation_context else slug
                result = self.calculation_context[key]

                if type(result) == float and result in (numpy.nan, numpy.inf):
                    raise ValueError(
                        _("%(test)s has a result of '%(test_result)s'") % {
                            'test': slug,
                            'test_result': str(result)
                        }
                    )
                else:
                    try:
                        # since the json test is happening in our code, we
                        # don't want to send full traceback information.
                        # instead, limit to not JSON serializable error
                        tb_limit = 0
                        json.dumps(result, cls=QATrackJSONEncoder)  # ensure result is JSON serializable
                        tb_limit = 5
                    except TypeError as e:
                        raise ValueError(_("%(test)s failed with error: %(error)s.") % {'test': slug, 'error': str(e)})

                formatted = utils.format_qc_value(result, self.formatters.get(slug))

                results[slug] = {
                    'value': result,
                    'formatted': formatted,
                    'error': None,
                    'user_attached': list(self.calculation_context.get("__user_attached__", [])),
                    'comment': self.calculation_context.get("__comment__"),
                }
                self.calculation_context[slug] = result
            except Exception:
                msg = traceback.format_exc(
                    limit=tb_limit, chain=True
                ).split("__QAT+COMP_")[-1].replace("<module>", slug)

                results[slug] = {
                    'value': None,
                    'error': _("Invalid Test Procedure: %(traceback)s") % {'traceback': msg},
                    'comment': "",
                    'user_attached': [],
                }
                deps_not_complete = any(self.data['tests'][s] in (None, "") for s in self.all_dependencies[slug])
                if deps_not_complete:
                    results[slug]['error'] = None
            finally:
                # clean up calculation context for next test
                to_clean = ['result'] + [k for k in self.calculation_context.keys() if k not in self.context_keys]
                to_clean = set([k for k in to_clean if k in self.calculation_context])
                for k in to_clean:
                    del self.calculation_context[k]

                del self.calculation_context['__user_attached__'][:]

        skips = self.calculation_context['UTILS'].skips

        return {"success": True, "errors": [], "results": results, "skips": skips}

    def set_formatters(self):
        """Set formatters for tests where applicable"""
        if self.defaults:
            # don't format default values since it can lead to confusion when comparing with old values
            self.formatters = {}
        else:
            self.formatters = {x.slug: x.formatting for x in self.all_tests if x.type in models.NUMERICAL_TYPES}

    def set_composite_test_data(self):
        """retrieve calculation procs for all composite tests"""

        if self.defaults:
            filter_ = lambda t: t.type not in models.CALCULATED_TYPES and t.calculation_procedure  # noqa: E731
        else:
            filter_ = lambda t: t.type in models.COMPOSITE_TYPES  # noqa: E731

        self.composite_tests = {
            t.slug: t.calculation_procedure for t in self.all_tests if filter_(t)
        }

    def set_test_types(self):
        """retrieve calculation procs for all composite tests"""
        self.test_types = {x.slug: x.type for x in self.all_tests}

    def set_calculation_context(self):
        """set up the environment that the composite test will be calculated in"""

        self.calculation_context = {}
        values = self.data.get("tests")
        meta_data = self.data.get("meta")

        tz = timezone.get_current_timezone()
        for d in ("work_completed", "work_started"):
            try:
                meta_data[d] = tz.localize(parse_datetime(meta_data[d]))
            except (TypeError, KeyError, AttributeError):
                pass

        if values is None:
            return

        refs, tols = get_context_refs_tols(self.unit, self.all_tests)

        comments = self.data.get("comments", {})
        skips = self.data.get("skips", {})
        self.calculation_context.update({
            "META": meta_data,
            "REFS": refs,
            "TOLS": tols,
            "UTILS": CompositeUtils(
                self.user,
                self.unit,
                self.test_list,
                meta_data,
                self.calculation_context,
                comments,
                skips,
            ),
        })

        self.calculation_context.update(DEFAULT_CALCULATION_CONTEXT)

        self.context_keys = list(self.calculation_context.keys())

        tz = timezone.get_current_timezone()
        for slug, val in values.items():

            self.context_keys.append(slug)

            if self.test_types.get(slug) == models.DATETIME:

                try:
                    dt = tz.localize(parse_datetime(val))
                    self.calculation_context[slug] = dt
                except:  # noqa: E722
                    self.calculation_context[slug] = None

            elif self.test_types.get(slug) == models.DATE:

                try:
                    self.calculation_context[slug] = parse_date(val)
                except:  # noqa: E722
                    self.calculation_context[slug] = None

            elif slug not in self.composite_tests:
                self.calculation_context[slug] = val

    def set_dependencies(self):
        """figure out composite dependencies of composite tests"""

        self.all_dependencies = {}
        self.dependencies = {}
        slugs = list(self.composite_tests.keys())
        all_slugs = list(self.data['tests'].keys())
        for slug in slugs:
            tokens = utils.tokenize_composite_calc(self.composite_tests[slug])
            comp_dependencies = [s for s in slugs if s in tokens and s != slug]
            self.dependencies[slug] = set(comp_dependencies)
            all_dependencies = [s for s in all_slugs if s in tokens and s != slug]
            self.all_dependencies[slug] = set(all_dependencies)

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

    json_encoder_class = QATrackJSONEncoder

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
    """View for selecting a unit to perform QC on"""

    template_name = 'units/unittype_list.html'
    active_only = True
    split_sites = True
    unit_serviceable_only = False

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
        if self.unit_serviceable_only:
            q = q.filter(unit__is_serviceable=True)

        units_ordering = 'unit__%s' % (settings.ORDER_UNITS_BY,)

        units_with_adhoc = set(q.filter(frequency=None).values_list("unit__number", flat=True).distinct())
        context['units_with_adhoc'] = units_with_adhoc

        if Site.objects.all().exists() and self.split_sites:

            unit_site_types = {}
            for s in Site.objects.all():
                unit_site_types[(s.slug, s.name)] = collections.defaultdict(list)
            if q.filter(unit__site__isnull=True).exists():
                unit_site_types[('zzzNonezzz', 'zzzNonezzz')] = collections.defaultdict(list)

            q = q.values(
                'unit',
                'unit__type__name',
                'unit__type__collapse',
                'unit__name',
                'unit__number',
                'unit__id',
                'unit__site__slug',
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

                unit['categories'] = get_unit_categories(unit['unit__id'])

                if unit['unit__site__name']:
                    key = (unit['unit__site__slug'], unit['unit__site__name'])
                    unit_site_types[key][(unit["unit__type__name"], unit["unit__type__collapse"])].append(unit)
                else:
                    unit_site_types[('zzzNonezzz', 'zzzNonezzz')][
                        (unit['unit__type__name'], unit['unit__type__collapse'])
                    ].append(unit)

            ordered = {}
            for s in unit_site_types:
                if len(unit_site_types[s]) == 0:
                    continue
                ordered[s] = sorted(
                    list(unit_site_types[s].items()), key=lambda x: min([u[units_ordering] for u in x[1]])
                )

            ordered = collections.OrderedDict(sorted(ordered.items(), key=lambda s: s[0]))

            context['split_sites'] = True

            split_by = max(3, 12 / max(1, len(ordered)))
            context['split_by'] = int(split_by)

        else:
            q = q.values('unit', 'unit__type__name', 'unit__type__collapse', 'unit__name', 'unit__number',
                         'unit__id').order_by(units_ordering).distinct()
            freq_qs = models.Frequency.objects.prefetch_related('unittestcollections__unit').all()

            unit_types = collections.defaultdict(list)
            for unit in q:
                unit['frequencies'] = freq_qs.filter(unittestcollections__unit_id=unit['unit__id']).distinct().values(
                    'slug', 'name'
                )
                unit['categories'] = get_unit_categories(unit['unit__id'])
                unit_types[(unit["unit__type__name"], unit["unit__type__collapse"])].append(unit)

            ordered = sorted(list(unit_types.items()), key=lambda x: min([u[units_ordering] for u in x[1]]))
            context['split_sites'] = False

        context['unit_types'] = ordered

        return context


def get_unit_categories(unit_id):

    if not settings.CHOOSE_UNIT_CATEGORY_DROPDOWN:
        return []

    qs = models.UnitTestInfo.objects.filter(
        unit_id=unit_id,
        test__category__parent=None,
    ).order_by(
        "test__category__name",
    ).values_list(
        "test__category__slug",
        "test__category__name",
    ).distinct()

    return qs


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
        """Find and order all :model:`qa.UnitTestInfo` objects for tests to be performed"""

        utis = models.UnitTestInfo.objects.filter(
            unit=self.unit_test_col.unit,
            test__in=self.all_tests,
            active=True,
        ).select_related(
            "reference",
            "test__category",
            "tolerance",
            "unit",
        ).prefetch_related("test__attachment_set")

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

    def form_invalid(self, form):
        """If the form is invalid, render the invalid form."""
        context = self.get_context_data(form=form)
        context['has_errors'] = True
        messages.error(
            self.request,
            _("Data was not submitted succesfully. Please resolve the errors below and try again."),
        )
        return self.render_to_response(context)

    @transaction.atomic
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
            context['has_errors'] = True
            messages.error(
                self.request,
                _("Data was not submitted succesfully. Please resolve the errors below and try again."),
            )
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
        # and save below to get due date set correctly
        self.object.save()

        self.create_tli_attachments()

        to_save = []

        attachments = []

        has_tli_comment = False
        if form.cleaned_data['comment']:
            has_tli_comment = True
            comment = Comment(
                submit_date=timezone.now(),
                user=self.request.user,
                content_object=self.object,
                comment=form.cleaned_data['comment'],
                site=get_current_site(self.request)
            )
            comment.save()

        for order, ti_form in enumerate(formset):

            attachments.extend(ti_form.attachments_to_process)

            ti = models.TestInstance(
                value=ti_form.cleaned_data.get("value"),
                string_value=ti_form.cleaned_data.get("string_value", ""),
                json_value=ti_form.cleaned_data.get("json_value", ""),
                date_value=ti_form.cleaned_data.get("date_value"),
                datetime_value=ti_form.cleaned_data.get("datetime_value"),
                skipped=ti_form.cleaned_data.get("skipped", False),
                comment=ti_form.cleaned_data.get("comment", ""),
                unit_test_info=ti_form.unit_test_info,
                reference=ti_form.unit_test_info.reference,
                tolerance=ti_form.unit_test_info.tolerance,
                status=status,
                order=order,
                created=self.object.created,
                created_by=self.request.user,
                modified_by=self.request.user,
                test_list_instance=self.object,
                work_started=self.object.work_started,
                work_completed=self.object.work_completed,
            )
            ti.calculate_pass_fail()
            if not self.user_set_status:
                ti.auto_review(has_tli_comment=has_tli_comment)

            to_save.append(ti)

        models.TestInstance.objects.bulk_create(to_save)

        set_attachment_owners(self.object, attachments)

        # set due date to account for any non default statuses
        self.object.unit_test_collection.set_due_date()

        if settings.USE_SERVICE_LOG:
            # service_events = form.cleaned_data.get('service_events', False)
            rtsqa_id = form.cleaned_data['rtsqa_id']

            # is there an existing rtsqa being linked?
            if rtsqa_id:
                rtsqa = sl_models.ReturnToServiceQA.objects.get(pk=rtsqa_id)
                rtsqa.test_list_instance = self.object
                rtsqa.save()

                sl_models.ServiceLog.objects.log_rtsqa_changes(self.request.user, rtsqa.service_event)

                # If tli needs review, update 'Unreviewed RTS QC' counter
                if not self.object.all_reviewed:
                    cache.delete(settings.CACHE_RTS_QA_COUNT)

            changed_se = self.object.update_all_reviewed()

            if len(changed_se) > 0:
                msg = _(
                    'Changed status of service event(s) %(service_event_ids)s to "%(serviceeventstatus_name)s".'
                ) % {
                    'service_event_ids': ', '.join(str(x) for x in changed_se),
                    'serviceeventstatus_name': sl_models.ServiceEventStatus.get_default().name,
                }
                messages.add_message(request=self.request, level=messages.INFO, message=msg)

        auto = form.cleaned_data.get("autosave_id")
        if auto:
            models.AutoSave.objects.filter(pk=auto).delete()

        if not self.object.in_progress:
            # TestListInstance & TestInstances have been successfully create, fire signal
            # to inform any listeners (e.g notifications.handlers.email_no_testlist_save)
            signals.testlist_complete.send(sender=self, instance=self.object, created=False)

        # let user know request succeeded and return to unit list
        messages.success(
            self.request,
            _("Successfully submitted %(test_list_name)s ") % {'test_list_name': self.object.test_list.name}
        )

        if settings.USE_SERVICE_LOG and form.cleaned_data['initiate_service']:
            return HttpResponseRedirect('%s?ib=%s' % (reverse('sl_new'), self.object.id))

        return HttpResponseRedirect(self.get_success_url())

    def create_tli_attachments(self):
        for idx, f in enumerate(self.request.FILES.getlist('tli_attachments')):
            comment = _("Uploaded %(current_datetime)s by %(username)s") % {
                'current_datetime': format_datetime(timezone.now()),
                'username': self.request.user.username
            }
            Attachment.objects.create(
                attachment=f,
                comment=comment,
                label=f.name,
                testlistinstance=self.object,
                created_by=self.request.user,
            )

    def get_context_data(self, **kwargs):
        context = super(PerformQA, self).get_context_data(**kwargs)

        # explicity refresh session expiry to prevent situation where a session
        # expires in between the time a user requests a page and then submits the page
        # causing them to lose all the data they entered
        self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        if models.TestInstanceStatus.objects.default() is None:
            messages.error(
                self.request,
                _("There must be at least one Test Status defined before performing a TestList"),
            )
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
        context['categories'] = sorted(set([x.test.category for x in self.unit_test_infos]), key=lambda c: c.name)
        context['current_day'] = self.actual_day + 1
        context["last_instance"] = self.unit_test_col.last_instance
        context['last_day'] = self.last_day
        context['borders'] = self.test_list.sublist_borders()
        context["autosaves"] = list(self.unit_test_col.autosave_set.order_by("-created").select_related("modified_by"))

        ndays = len(self.unit_test_col.tests_object)
        if ndays > 1:
            context['days'] = self.unit_test_col.tests_object.days_display()

        in_progress = models.TestListInstance.objects.in_progress().filter(
            unit_test_collection=self.unit_test_col, test_list=self.test_list
        )

        context['tests_object_type'] = self.unit_test_col.tests_object.__class__.__name__

        context["test_list"] = self.test_list
        context["in_progress"] = in_progress
        context["unit_test_infos"] = json.dumps(self.template_unit_test_infos(), cls=QATrackJSONEncoder)
        context["unit_test_collection"] = self.unit_test_col
        context["contacts"] = list(Contact.objects.all().order_by("name"))

        rtsqa_id = None
        if settings.USE_SERVICE_LOG:
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

        context['top_divs_span'] = 1
        has_perms = (
            self.request.user.has_perm('qa.can_review') or
            self.request.user.has_perm('qa.can_review_own_tests') or
            self.request.user.has_perm('qa.can_override_date')
        )
        if has_perms:
            context['top_divs_span'] += 1
        if settings.USE_SERVICE_LOG and rtsqa_id is not None:
            context['top_divs_span'] += 1
        context['top_divs_span'] = int(12 / context['top_divs_span']) if context['top_divs_span'] > 0 else 12

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

    @transaction.atomic
    def form_valid(self, form):

        self.form = form

        context = self.get_context_data(form=form)
        formset = context["formset"]

        if formset.is_valid():
            self.object = form.save(commit=False)
            self.has_tli_comment = self.object.comments.all().exists()

            initially_requires_reviewed = not self.object.all_reviewed

            status_pk = None
            if "status" in form.fields:
                status_pk = form["status"].value()
            self.set_status_object(status_pk)

            self.update_test_list_instance()

            has_existing_attachments = set(
                Attachment.objects.filter(testinstance__in=self.object.testinstance_set.all()).values_list(
                    "testinstance_id",
                    flat=True,
                )
            )

            for ti_form in formset:

                ti = ti_form.save(commit=False)

                self.update_test_instance(ti)

                if ti.id in has_existing_attachments:
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
            if settings.USE_SERVICE_LOG:
                changed_se = self.object.update_all_reviewed()

                if len(changed_se) > 0:
                    msg = _(
                        'Changed status of service event(s) %(service_event_ids)s to "%(serviceeventstatus_name)s".'
                    ) % {
                        'service_event_ids': ', '.join(str(x) for x in changed_se),
                        'serviceeventstatus_name': sl_models.ServiceEventStatus.get_default().name,
                    }
                    messages.add_message(request=self.request, level=messages.INFO, message=msg)
                if initially_requires_reviewed != self.object.all_reviewed:
                    for se in sl_models.ServiceEvent.objects.filter(returntoserviceqa__test_list_instance=self.object):
                        sl_models.ServiceLog.objects.log_rtsqa_changes(self.request.user, se)

            if not self.object.in_progress:
                try:
                    signals.testlist_complete.send(sender=self, instance=self.object, created=False)
                except:  # noqa: E722
                    msg = _('Error sending notification email.')
                    messages.add_message(request=self.request, message=msg, level=messages.ERROR)

            auto = form.cleaned_data.get("autosave_id")
            if auto:
                models.AutoSave.objects.filter(pk=auto).delete()

            # let user know request succeeded and return to unit list
            messages.success(
                self.request,
                _("Successfully submitted %(test_list_name)s") % {'test_list_name': self.object.test_list.name},
            )

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
            self.object.reviewed = now
            self.object.reviewed_by = self.request.user
            self.object.all_reviewed = True

        if self.object.work_completed is None:
            self.object.work_completed = now

        self.object.save()

        if self.request.FILES:
            self.update_attachments()

    def update_attachments(self):
        for attach in self.object.attachment_set.all():
            attach.delete()

        for idx, f in enumerate(self.request.FILES.getlist('tli_attachments')):
            comment = _("Uploaded %(current_datetime)s by %(username)s") % {
                'current_datetime': format_datetime(timezone.now()),
                'username': self.request.user.username
            }
            Attachment.objects.create(
                attachment=f,
                comment=comment,
                label=f.name,
                testlistinstance=self.object,
                created_by=self.request.user,
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
                ti.auto_review(has_tli_comment=self.has_tli_comment)

            ti.save(calculate_pass_fail=False)
        except ZeroDivisionError:

            ti.skipped = True
            ti.comment = _(
                "Tried to calculate percent diff with a zero reference value. "
                "Original value was %(test_instance_value)s"
            ) % {'test_instance_value': ti.value}
            ti.value = None
            ti.save()

            logger.error(_(
                "Tried to calculate percent diff with a zero reference value. UTI=%(unit_test_info_id)d"
            ) % {'unit_test_info_id': ti.unit_test_info.pk})
            msg = _(
                "Please call physics. Test %(test_name)s is configured incorrectly on this unit. "
                "Tried to calculate percent diff with a zero reference value."
            ) % {'test_name': ti.unit_test_info.test.name}
            messages.error(self.request, msg)

    def template_unit_test_infos(self):
        """prepare the unit test infos for rendering in template"""

        template_utis = []
        for uti in self.unit_test_infos:
            ref, tol = self.prev_ref_tols[uti.pk]
            template_utis.append({
                "id": uti.pk,
                "test": model_to_dict(uti.test),
                "reference": model_to_dict(ref) if ref else None,
                "tolerance": model_to_dict(tol) if tol else None,
            })
        return template_utis

    def get_context_data(self, **kwargs):

        context = super(EditTestListInstance, self).get_context_data(**kwargs)
        uti_pks = [f.instance.unit_test_info.pk for f in context["formset"]]
        self.prev_ref_tols = {
            f.instance.unit_test_info.pk: (f.instance.reference, f.instance.tolerance) for f in context["formset"]
        }
        utis = models.UnitTestInfo.objects.filter(pk__in=uti_pks).select_related(
            "unit",
            "test__category",
        ).prefetch_related(
            "test__attachment_set",
        )
        self.unit_test_infos = list(sorted(utis, key=lambda x: uti_pks.index(x.pk)))

        context["unit_test_infos"] = json.dumps(self.template_unit_test_infos(), cls=QATrackJSONEncoder)

        context['attachments'] = context['test_list'].attachment_set.all(
        ) | self.object.unit_test_collection.tests_object.attachment_set.all()

        context['top_divs_span'] = 0
        if self.request.user.has_perm('qa.can_review') or self.request.user.has_perm(
                'qa.can_review_own_tests') or self.request.user.has_perm('qa.can_override_date'):
            context['top_divs_span'] += 1
        if len(context['attachments']) > 0:
            context['top_divs_span'] += 1
        if settings.USE_SERVICE_LOG and (context['form'].instance.pk or context['rtsqa_id'] is not None):
            context['top_divs_span'] += 1
        context['top_divs_span'] = int(12 / context['top_divs_span']) if context['top_divs_span'] > 0 else 12

        context["contacts"] = list(Contact.objects.all().order_by("name"))

        if self.object.unit_test_collection.tests_object.__class__.__name__ == 'TestListCycle':
            context['cycle_name'] = self.object.unit_test_collection.name

        context["autosaves"] = list(
            self.object.unit_test_collection.autosave_set.order_by("-created").select_related("modified_by")
        )

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

    def get_queryset(self, *args, **kwargs):
        return models.TestListInstance.objects.in_progress(user=self.request.user)

    def get_icon(self):
        return 'fa-play'

    def get_page_title(self):
        return _("In Progress Test Lists")


def autosave(request):

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'autosave_id': None})

    tz = timezone.get_current_timezone()
    for d in ("work_completed", "work_started"):
        try:
            data['meta'][d] = tz.localize(parse_datetime(data['meta'][d]))
        except (TypeError, KeyError, AttributeError):
            data['meta'][d] = None

    try:
        saved = models.AutoSave.objects.get(pk=data['autosave_id'] or None)
    except models.AutoSave.DoesNotExist:
        saved = models.AutoSave.objects.create(
            unit_test_collection_id=data['meta']['unit_test_collection_id'],
            test_list_instance_id=data.get('test_list_instance') or None,
            created_by=request.user,
            modified_by=request.user,
            test_list_id=data['meta']['test_list_id'],
            data={},
        )

    saved.work_started = data['meta']['work_started'] or timezone.now()
    saved.work_completed = data['meta']['work_completed']
    try:
        saved.day = int(data['meta']['cycle_day']) - 1
    except (ValueError, TypeError):
        pass

    saved.modified_by = request.user
    saved.data = {
        'tests': data['tests'],
        'comments': data['comments'],
        'skips': data['skips'],
        'tli_comment': data['tli_comment'],
    }
    saved.save()

    return JsonResponse({'ok': True, 'autosave_id': saved.pk})


def autosave_load(request):
    autosave_id = request.GET.get("autosave_id")
    auto = get_object_or_404(models.AutoSave, pk=autosave_id)

    data = {
        'meta': {
            'work_started': timezone.localtime(auto.work_started) if auto.work_started else None,
            'work_completed': timezone.localtime(auto.work_completed) if auto.work_completed else None,
        },
        'data': auto.data,
    }

    return JsonResponse(data, encoder=QATrackJSONEncoder)


class FrequencyList(UTCList):
    """List :model:`qa.UnitTestCollection`s for requested :model:`qa.Frequency`s"""

    def get_queryset(self):
        """filter queryset by frequency"""

        qs = super(FrequencyList, self).get_queryset()

        freqs = self.kwargs["frequency"].split("/")
        self.frequencies = models.Frequency.objects.filter(slug__in=freqs)

        q = Q(frequency__in=self.frequencies)
        self.has_ad_hoc = False
        if "ad-hoc" in freqs:
            self.has_ad_hoc = True
            q |= Q(frequency=None)

        return qs.filter(q).distinct()

    def get_page_title(self):
        names = ", ".join([x.name if x else "ad-hoc" for x in self.frequencies])
        if self.has_ad_hoc:
            names = _("Ad Hoc ") + names.strip()
        return _("%(frequency_names)s Test Lists") % {'frequency_names': names}


class FrequencyTree(PermissionRequiredMixin, TemplateView):
    """
    View for users to edit an existing :model:`qa.TestListInstance` and
    its children :model:`qa.TestInstance`s.

    Note: Some of this code is duplicated in :view:`qa.views.perform.PerformQA`
    and the common parts may be able to be refactored into a mixin.
    """

    template_name = 'qa/frequency_tree.html'
    permission_required = "qa.add_testlistinstance"
    raise_exception = True

    def get_context_data(self, *args, **kwargs):

        context = super().get_context_data(*args, **kwargs)
        context['tree'] = BootstrapFrequencyTree(self.request.user.groups.all()).generate()
        return context


class DueAndOverdue(UTCList):

    page_title = _l("Due & Overdue QC")

    def get_queryset(self):
        today = timezone.now().astimezone(timezone.get_current_timezone()).date()
        qs = super().get_queryset()
        return qs.exclude(due_date=None).filter(due_date__lt=today)


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
        freq_names = ", ".join([x.name if x else "ad-hoc" for x in self.frequencies])
        if self.has_ad_hoc:
            freq_names = _("Ad Hoc ") + freq_names.strip()
        title = '%(unit_names)s %(frequency_names)s Test Lists' % {
            'unit_names': ", ".join([x.name for x in self.units]),
            'frequency_names': freq_names,
        }

        return title


class CategoryTree(PermissionRequiredMixin, TemplateView):
    """
    View for users to edit an existing :model:`qa.TestListInstance` and
    its children :model:`qa.TestInstance`s.

    Note: Some of this code is duplicated in :view:`qa.views.perform.PerformQA`
    and the common parts may be able to be refactored into a mixin.
    """

    template_name = 'qa/category_tree.html'
    permission_required = "qa.add_testlistinstance"
    raise_exception = True

    def get_context_data(self, *args, **kwargs):

        context = super().get_context_data(*args, **kwargs)
        context['tree'] = BootstrapCategoryTree(self.request.user.groups.all()).generate()
        return context


class CategoryList(UTCList):

    def get_queryset(self):
        """filter queryset by test category"""

        qs = super(CategoryList, self).get_queryset()

        categories = self.kwargs["category"].split("/")
        self.categories = models.Category.objects.filter(slug__in=categories)
        all_cat_ids = []
        for cat in self.categories:
            for desc in cat.get_descendants(True):
                all_cat_ids.append(desc.id)

        q = (
            Q(test_list__testlistmembership__test__category_id__in=all_cat_ids) |
            Q(test_list__children__child__testlistmembership__test__category_id__in=all_cat_ids) |
            Q(test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category_id__in=all_cat_ids) |  # noqa: E501
            Q(test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category_id__in=all_cat_ids)  # noqa: E501
        )  # yapf: disable

        return qs.filter(q).distinct()

    def get_page_title(self):
        return _("Test Lists for Categories: %(category_names)s") % {
            'category_names': ", ".join([x.name for x in self.categories])
        }


class UnitCategoryList(CategoryList):
    """
    List :model:`qa.UnitTestCollection`s for requested :model:`unit.Unit`s
    and :model:`qa.Category`s.
    """

    def get_queryset(self):
        """filter queryset by Unit"""

        qs = super().get_queryset()
        self.units = Unit.objects.filter(number__in=self.kwargs["unit_number"].split("/"))
        return qs.filter(unit__in=self.units)

    def get_page_title(self):
        title = _('Test Lists for Units: %(unit_names)s and Categories: %(category_names)s') % {
            'unit_names': ", ".join([x.name for x in self.units]),
            'category_names': ", ".join([x.name for x in self.categories]),
        }
        return title


class UnitList(UTCList):
    """ List :model:`qa.UnitTestCollection`s for requested :model:`unit.Unit`s """

    def get_queryset(self):
        """filter queryset by frequency"""
        qs = super(UnitList, self).get_queryset()
        self.units = Unit.objects.filter(number__in=self.kwargs["unit_number"].split("/"))
        return qs.filter(unit__in=self.units)

    def get_page_title(self):
        title = '%(unit_names)s Test Lists' % {'unit_names': ", ".join([x.name for x in self.units])}
        return title


class SiteList(UTCList):
    """ List :model:`qa.UnitTestCollection`s for requested :model:`unit.Site`s """

    def get_queryset(self):

        qs = super().get_queryset()

        sites = self.kwargs["site"].split("/")
        self.sites = Site.objects.filter(slug__in=sites)

        q = Q(unit__site__in=self.sites)
        self.has_other = False
        if "other" in sites:
            self.has_other = True
            q |= Q(unit__site=None)

        return qs.filter(q).distinct()

    def get_page_title(self):
        names = ", ".join([x.name if x else "other" for x in self.sites])
        if self.has_other:
            names = _("Other") + names.strip()
        return _("%(site_names)s Test Lists") % {'site_names': names}
