import collections
import json

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy
import scipy

from .. import models
from .base import JSONResponseMixin
from qatrack.qa.control_chart import control_chart
from qatrack.units.models import Unit, UnitType

#============================================================================
class ChartView(TemplateView):
    """View responsible for rendering the charts page.  The data used
    for rendering charts is provided by the subclasses of BaseChartData below
    """

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

        self.unit_frequencies = collections.defaultdict(lambda: collections.defaultdict(list))

        for utc in utcs:
            if utc["frequency"] is None:
                utc["frequency"] = 0
            unit = utc["unit"]
            freq = utc["frequency"]
            if utc["content_type"] == tlc_content_type:
                test_list = utc["testlistcycle__test_lists"]
            else:
                test_list = utc["testlist"]

            self.unit_frequencies[unit][freq].append(test_list)

        # uniquify unit/freq lists
        for utc in utcs:
            unit = utc["unit"]
            freq = utc["frequency"]
            self.unit_frequencies[unit][freq] = list(sorted(set(self.unit_frequencies[unit][freq])))

        self.test_data = {
            "test_lists": {},
            "unit_frequency_lists": self.unit_frequencies,
        }

        for test_list in self.test_lists:

            tests = [x.pk for x in test_list.tests.all()]
            if test_list.sublists:
                for sublist in test_list.sublists.all():
                    tests.extend(list(sublist.tests.values_list("pk", flat=True)))

            self.test_data["test_lists"][test_list.pk] = tests

        return json.dumps(self.test_data)

    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        """add default dates to context"""
        context = super(ChartView, self).get_context_data(**kwargs)

        self.set_test_lists()
        self.set_tests()

        test_data = self.create_test_data()

        c = {
            "from_date": timezone.now().date()-timezone.timedelta(days=365),
            "to_date": timezone.now().date()+timezone.timedelta(days=1),
            "frequencies": models.Frequency.objects.all(),
            "tests": self.tests,
            "test_lists": self.test_lists,
            "categories": models.Category.objects.all(),
            "statuses": models.TestInstanceStatus.objects.all(),
            "units": Unit.objects.all().select_related("type"),
            "test_data": test_data,
            "chart_data_url": reverse("chart_data"),
            "control_chart_url": reverse("control_chart"),

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
        from_date = self.get_date("from_date", now-timezone.timedelta(days=365))
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


#============================================================================
class BasicChartData(JSONResponseMixin, BaseChartView):
    pass


#============================================================================
class ControlChartImage(BaseChartView):
    """Return a control chart image from given qa data"""

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
            self.get_number_from_request("width", 700)/dpi,
            self.get_number_from_request("height", 480)/dpi,
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
        if n_baseline_subgroups < 1 or n_baseline_subgroups > len(data)/subgroup_size:
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

#============================================================================
class ExportToCSV(View):
    """A simple api wrapper to give exported api data a filename for downloads"""

    #----------------------------------------------------------------------
    def get(self, request, *args, **kwargs):
        """takes request, passes it to api and returns a file"""
        response = ValueResource().get_list(request)
        response["Content-Disposition"] = 'attachment; filename=exported_data.csv'
        return response

