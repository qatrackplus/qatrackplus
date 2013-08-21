import collections
import itertools
import json
import textwrap

from django.conf import settings
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
from qatrack.qa.control_chart import control_chart
from qatrack.units.models import Unit
from qatrack.qa.utils import SetEncoder
from braces.views import JSONResponseMixin, PermissionRequiredMixin


local_tz = timezone.get_current_timezone()


#============================================================================
class ChartView(PermissionRequiredMixin, TemplateView):
    """View responsible for rendering the charts page.  The data used
    for rendering charts is provided by the subclasses of BaseChartData below
    """

    permission_required = "qa.can_view_charts"

    template_name = "qa/charts.html"

    #----------------------------------------------------------------------
    def create_test_data(self):
        # note: leaving off the distinct queryhere results in a factor of 3 speedup
        # (250ms vs 750ms for 150k total test instances)  for a sqlite query.  The
        # distinctness/uniqueness is guarannteed by using sets below.

        q = models.TestInstance.objects.values_list(
            "unit_test_info__unit",
            "unit_test_info__test",
            "unit_test_info__test__type",
            "test_list_instance__test_list",
            "test_list_instance__unit_test_collection__frequency",
        )

        data = {
            'test_lists': collections.defaultdict(set),
            'unit_frequency_lists': collections.defaultdict(lambda: collections.defaultdict(set)),
        }

        for unit, test, test_type, test_list, frequency in q:
            if test_type not in (models.UPLOAD, ):
                data["test_lists"][test_list].add(test)
                frequency = frequency or 0
                data["unit_frequency_lists"][unit][frequency].add(test_list)

        return data

    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        """add default dates to context"""
        context = super(ChartView, self).get_context_data(**kwargs)

        self.set_test_lists()
        self.set_tests()

        test_data = self.create_test_data()
        now = timezone.now().astimezone(timezone.get_current_timezone()).date()

        c = {
            "from_date": now - timezone.timedelta(days=365),
            "to_date": now + timezone.timedelta(days=1),
            "frequencies": models.Frequency.objects.all(),
            "tests": self.tests,
            "test_lists": self.test_lists,
            "categories": models.Category.objects.all(),
            "statuses": models.TestInstanceStatus.objects.all(),
            "units": Unit.objects.values("pk", "name"),
            "test_data": json.dumps(test_data, cls=SetEncoder)
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

        self.get_plot_data()
        table = self.create_data_table()
        resp = self.render_to_response({"data": self.plot_data, "table": table})

        return resp

    #----------------------------------------------------------------------
    def create_data_table(self):

        headers = []
        max_len = 0
        cols = []

        r = lambda ref: ref if ref is not None else ""

        for name, points in self.plot_data.iteritems():
            headers.append(name)
            col = [(p["display_date"], p["display"], r(p["reference"])) for p in points]
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
            rows.append(row)

        context = Context({
            "ncols": 3 * len(rows[0]) if rows else 0,
            "rows": rows,
            "headers": headers
        })
        template = get_template("qa/qa_data_table.html")

        return template.render(context)

    #----------------------------------------------------------------------
    def get_date(self, key, default):
        #datetime strings coming in will be in local time, make sure they get
        #converted to utc

        try:
            d = timezone.datetime.strptime(self.request.GET.get(key), settings.SIMPLE_DATE_FORMAT)
        except:
            d = default

        if timezone.is_naive(d):
            d = timezone.make_aware(d, timezone.get_current_timezone())

        return d.astimezone(timezone.utc)

    #---------------------------------------------------------------
    def convert_date(self, date):
        return date.isoformat()

    #---------------------------------------------------------------
    def test_instance_to_point(self, ti):

        point = {
            "act_high": None, "act_low": None, "tol_low": None, "tol_high": None,
            "date": self.convert_date(timezone.make_naive(ti.work_completed, local_tz)),
            "display_date": ti.work_completed,
            "value": ti.value,
            "display": ti.value_display(),
            "reference": ti.reference.value if ti.reference else None,
        }
        if ti.tolerance is not None and ti.reference is not None:
            point.update(ti.tolerance.tolerances_for_value(ti.reference.value))

        return point

    #----------------------------------------------------------------------
    def get_plot_data(self):

        self.plot_data = {}

        now = timezone.now()
        from_date = self.get_date("from_date", now - timezone.timedelta(days=365))
        to_date = self.get_date("to_date", now)

        tests = self.request.GET.getlist("tests[]", [])
        test_lists = self.request.GET.getlist("test_lists[]", [])
        units = self.request.GET.getlist("units[]", [])
        statuses = self.request.GET.getlist("statuses[]", [])

        if not (tests and test_lists and units and statuses):
            return

        tests = models.Test.objects.filter(pk__in=tests)
        test_lists = models.TestList.objects.filter(pk__in=test_lists)
        units = Unit.objects.filter(pk__in=units)
        statuses = models.TestInstanceStatus.objects.filter(pk__in=statuses)

        for tl, t, u in itertools.product(test_lists, tests, units):
            tis = models.TestInstance.objects.filter(
                test_list_instance__test_list=tl,
                unit_test_info__test=t,
                unit_test_info__unit=u,
                status__pk__in=statuses,
                work_completed__gte=from_date,
                work_completed__lte=to_date,
            ).select_related(
                "reference", "tolerance", "unit_test_info__test", "unit_test_info__unit", "status",
            ).order_by(
                "work_completed"
            )
            if tis:
                name = "%s - %s :: %s" % (u.name, tl.name, t.name)
                self.plot_data[name] = [self.test_instance_to_point(ti) for ti in tis]

    #---------------------------------------------------------------------------
    def render_to_response(self, context):
        return self.render_json_response(context)


#============================================================================
class BasicChartData(PermissionRequiredMixin, JSONResponseMixin, BaseChartView):

    permission_required = "qa.can_view_charts"


#============================================================================
class ControlChartImage(PermissionRequiredMixin, BaseChartView):
    """Return a control chart image from given qa data"""

    permission_required = "qa.can_view_charts"

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

    #---------------------------------------------------------------
    def get_plot_data(self):
        """only use one data series"""
        super(ControlChartImage, self).get_plot_data()
        if self.plot_data:
            self.plot_data = dict([self.plot_data.popitem()])

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
            name, points = context["data"].items()[0]
            dates, data = zip(*[(ti["date"], ti["value"]) for ti in points])

        n_baseline_subgroups = self.get_number_from_request("n_baseline_subgroups", 2, dtype=int)
        n_baseline_subgroups = max(2, n_baseline_subgroups)

        subgroup_size = self.get_number_from_request("subgroup_size", 2, dtype=int)
        if not (1 < subgroup_size < 100):
            subgroup_size = 1

        include_fit = self.request.GET.get("fit_data", "") == "true"

        response = HttpResponse(mimetype="image/png")
        if n_baseline_subgroups < 1 or n_baseline_subgroups > len(data) / subgroup_size:
            fig.text(0.1, 0.9, "Not enough data for control chart", fontsize=20)
            canvas.print_png(response)
        else:
            try:
                control_chart.display(fig, numpy.array(data), subgroup_size, n_baseline_subgroups, fit=include_fit, dates=dates)
                fig.autofmt_xdate()
                canvas.print_png(response)
            except (RuntimeError, OverflowError) as e:  #pragma: nocover
                fig.clf()
                msg = "There was a problem generating your control chart:\n%s" % str(e)
                fig.text(0.1, 0.9, "\n".join(textwrap.wrap(msg, 40)), fontsize=12)
                canvas.print_png(response)

        return response
