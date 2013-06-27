import collections
import json
import textwrap

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponse
from django.template import Context
from django.template.loader import get_template
from django.utils import timezone
from django.views.generic import TemplateView, View

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy

from .. import models
from qatrack.qa.api import ValueResource
from qatrack.qa.control_chart import control_chart
from qatrack.units.models import Unit

from braces.views import JSONResponseMixin, PermissionRequiredMixin

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

#============================================================================
class ChartView(PermissionRequiredMixin, TemplateView):
    """View responsible for rendering the charts page.  The data used
    for rendering charts is provided by the subclasses of BaseChartData below
    """

    permission_required = "qa.can_view_history"

    template_name = "qa/charts.html"

    #----------------------------------------------------------------------
    def create_test_data(self):
        # note: leaving off the distinct queryhere results in a factor of 3 speedup
        # (250ms vs 750ms for 150k total test instances)  for a sqlite query.  The
        # distinctness/uniqueness is guarannteed by using sets below.

        q = models.TestInstance.objects.values_list(
            "unit_test_info__unit",
            "unit_test_info__test",
            "test_list_instance__test_list",
            "test_list_instance__unit_test_collection__frequency"
        )#.distinct()

        data = {
            'test_lists' : collections.defaultdict(set),
            'unit_frequency_lists':collections.defaultdict(lambda: collections.defaultdict(set)),
        }

        for unit, test, test_list, frequency in q:
            data["test_lists"][test_list].add(test)
            data["unit_frequency_lists"][unit][frequency].add(test_list)

        return json.dumps(data,cls=SetEncoder)


    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        """add default dates to context"""
        context = super(ChartView, self).get_context_data(**kwargs)

        self.set_test_lists()
        self.set_tests()

        test_data = self.create_test_data()

        c = {
            "from_date": timezone.now().date() - timezone.timedelta(days=365),
            "to_date": timezone.now().date() + timezone.timedelta(days=1),
            "frequencies": models.Frequency.objects.all(),
            "tests": self.tests,
            "test_lists": self.test_lists,
            "categories": models.Category.objects.all(),
            "statuses": models.TestInstanceStatus.objects.all(),
            "units": Unit.objects.values("pk","name"),
            "test_data": test_data,
            "chart_data_url": reverse("chart_data"),
            "control_chart_url": reverse("control_chart"),

        }
        context.update(c)
        return context

    #----------------------------------------------------------------------
    def set_test_lists(self):
        """self.test_lists is set to all test lists that have been completed
        one or more times"""

        self.test_lists = models.TestList.objects.annotate(
            instance_count=Count("testlistinstance")
        ).filter(
            instance_count__gt=0
        ).order_by(
            "name"
        ).values(
            "pk", "description", "name",
        )
    #----------------------------------------------------------------------
    def set_tests(self):
        """self.tests is set to all tests that have been completed
        one or more times"""
        self.tests = models.Test.objects.order_by(
            "name"
        ).values(
            "pk", "category", "name", "description",
        )

#============================================================================
class BaseChartView(View):
    ISO_FORMAT = False

    #----------------------------------------------------------------------
    def get(self, request):

        data = self.get_plot_data()
        table = self.create_data_table()
        resp = self.render_to_response({"data": data, "table": table})

        return resp

    #----------------------------------------------------------------------
    def create_data_table(self):

        utis = list(set([x.unit_test_info for x in self.tis]))

        headers = []
        max_len = 0
        cols = []
        for uti in utis:
            headers.append("%s %s" % (uti.unit.name, uti.test.name))
            r = lambda x: ti.reference.value if ti.reference else ""
            col = [(ti.work_completed, ti.value_display(), r(ti)) for ti in self.tis if ti.unit_test_info == uti]
            cols.append(col)
            max_len = max(len(col), max_len)

        rows = []
        for idx in range(max_len):
            row = []
            for col in cols:
                try:
                    row.append(col[idx])
                except IndexError:
                    row.append(["", ""])
                    pass
            rows.append(row)

        context = Context({
            "ncols": 3*len(rows[0]) if rows else 0,
            "rows": rows,
            "headers": headers
        })
        template = get_template("qa/qa_data_table.html")

        return template.render(context)

    #----------------------------------------------------------------------
    def get_date(self, key, default):
        try:
            d = timezone.datetime.strptime(self.request.GET.get(key), settings.SIMPLE_DATE_FORMAT)
        except:
            d = default

        if timezone.is_naive(d):
            d = timezone.make_aware(d, timezone.get_current_timezone())

        return d

    #---------------------------------------------------------------------------
    def convert_date(self, dt):
        return dt.isoformat()

    #----------------------------------------------------------------------
    def get_plot_data(self):

        tests = self.request.GET.getlist("tests[]", [])
        units = self.request.GET.getlist("units[]", [])
        statuses = self.request.GET.getlist("statuses[]", models.TestInstanceStatus.objects.values_list("pk", flat=True))

        now = timezone.datetime.now()
        from_date = self.get_date("from_date", now - timezone.timedelta(days=365))
        to_date = self.get_date("to_date", now)

        self.tis = models.TestInstance.objects.filter(
            unit_test_info__test__pk__in=tests,
            unit_test_info__unit__pk__in=units,
            status__pk__in=statuses,
            work_completed__gte=from_date,
            work_completed__lte=to_date,
        ).select_related(
            "reference", "tolerance", "status", "unit_test_info", "unit_test_info__test", "unit_test_info__unit", "status"
        ).order_by(
            "work_completed"
        )

        vals_dict = lambda: {"data": [], "values": [], "dates": [], "references": [], "act_low": [], "tol_low": [], "tol_high": [], "act_high": []}
        data = collections.defaultdict(vals_dict)

        for ti in self.tis:
            uti = ti.unit_test_info
            d = timezone.make_naive(ti.work_completed, timezone.get_current_timezone())
            d = self.convert_date(d)
            data[uti.pk]["data"].append([d, ti.value])
            data[uti.pk]["values"].append(ti.value)

            if ti.reference is not None:
                data[uti.pk]["references"].append(ti.reference.value)
            else:
                data[uti.pk]["references"].append(None)

            if ti.tolerance is not None and ti.reference is not None:
                tols = ti.tolerance.tolerances_for_value(ti.reference.value)
            else:
                tols = {"act_high": None, "act_low": None, "tol_low": None, "tol_high": None}
            for k, v in tols.items():
                data[uti.pk][k].append(v)

            data[uti.pk]["dates"].append(d)
            data[uti.pk]["unit"] = {"name": uti.unit.name, "pk": uti.unit.pk}
            data[uti.pk]["test"] = {"name": uti.test.name, "pk": uti.test.pk}

        return data

    #---------------------------------------------------------------------------
    def render_to_response(self, context):
        return self.render_json_response(context)

#============================================================================
class BasicChartData(PermissionRequiredMixin, JSONResponseMixin, BaseChartView):

    permission_required = "qa.can_view_history"


#============================================================================
class ControlChartImage(PermissionRequiredMixin, BaseChartView):
    """Return a control chart image from given qa data"""

    permission_required = "qa.can_view_history"

    #---------------------------------------------------------------------------
    def convert_date(self, dt):
        return dt

    #----------------------------------------------------------------------
    def get_number_from_request(self, param, default, dtype=float):
        try:
            v = dtype(self.request.GET.get(param, default))
        except:
            v = default
        return v

    #----------------------------------------------------------------------
    def render_to_response(self, context):

        fig = Figure(dpi=72, facecolor="white")
        dpi = fig.get_dpi()
        fig.set_size_inches(
            self.get_number_from_request("width", 700) / dpi,
            self.get_number_from_request("height", 480) / dpi,
        )
        canvas = FigureCanvas(fig)

        dates, data = [], []

        if context["data"] and context["data"].values():

            for d, v in context["data"].values()[0]["data"]:
                if None not in (d, v):
                    dates.append(d)
                    data.append(v)

        n_baseline_subgroups = self.get_number_from_request("n_baseline_subgroups", 2, dtype=int)
        n_baseline_subgroups = max(2, n_baseline_subgroups)

        subgroup_size = self.get_number_from_request("subgroup_size", 2, dtype=int)
        if subgroup_size < 1 or subgroup_size > 100:
            subgroup_size = 1

        if self.request.GET.get("fit_data", "") == "true":
            include_fit = True
        else:
            include_fit = False

        response = HttpResponse(mimetype="image/png")
        if n_baseline_subgroups < 1 or n_baseline_subgroups > len(data) / subgroup_size:
            fig.text(0.1, 0.9, "Not enough data for control chart", fontsize=20)
            canvas.print_png(response)
        else:
            try:
                control_chart.display(fig, numpy.array(data), subgroup_size, n_baseline_subgroups, fit=include_fit, dates=dates)
                fig.autofmt_xdate()

                canvas.print_png(response)

            except (RuntimeError, OverflowError) as e:
                fig.clf()
                msg = "There was a problem generating your control chart:\n"
                msg += str(e)
                fig.text(0.1, 0.9, "\n".join(textwrap.wrap(msg, 40)), fontsize=12)
                canvas.print_png(response)

        return response

