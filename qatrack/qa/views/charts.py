import collections
import itertools
import json
import textwrap

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q, F, Case, When, IntegerField
from django.http import HttpResponse
from django.template import Context
from django.template.loader import get_template
from django.utils import timezone
from django.views.generic import TemplateView, View

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy
numpy.seterr(all='raise')

from .. import models
from qatrack.service_log import models as sl_models
from qatrack.qa.control_chart import control_chart
from qatrack.units.models import Unit
from qatrack.qa.utils import SetEncoder
from braces.views import JSONResponseMixin, PermissionRequiredMixin


JSON_CONTENT_TYPE = "application/json"


local_tz = timezone.get_current_timezone()


def get_test_lists_for_unit_frequencies(request):

    units = request.GET.getlist("units[]") or Unit.objects.values_list("pk", flat=True)
    frequencies = request.GET.getlist("frequencies[]")

    if '0' in frequencies:
        frequencies.remove('0')
        frequencies.append(None)

    if not frequencies:
        frequencies = list(models.Frequency.objects.values_list("pk", flat=True)) + [None]
    #
    # include_inactive = request.GET.get("inactive") == "true"

    # active = None if include_inactive else True

    test_lists = models.get_utc_tl_ids(units=units, frequencies=frequencies)

    json_context = json.dumps({"test_lists": test_lists})

    return HttpResponse(json_context, content_type=JSON_CONTENT_TYPE)


def get_tests_for_test_lists(request):

    test_lists = request.GET.getlist("test_lists[]") or models.TestList.objects.values_list("pk", flat=True)

    tests = []
    for pk in test_lists:
        tl = models.TestList.objects.get(pk=pk)
        tests.extend([t.pk for t in tl.ordered_tests() if t.chart_visibility])

    json_context = json.dumps({"tests": tests})
    return HttpResponse(json_context, content_type=JSON_CONTENT_TYPE)


class ChartView(PermissionRequiredMixin, TemplateView):
    """View responsible for rendering the main charts user interface."""

    permission_required = "qa.can_view_charts"
    raise_exception = True

    template_name = "qa/charts.html"

    def get_context_data(self, **kwargs):
        """
        Add all relevent filters to context. test_data contains all the
        tests grouped by test list/unit/frequency and is dumped as a json
        object for use on client side.
        """

        context = super(ChartView, self).get_context_data(**kwargs)

        self.set_test_lists()
        self.set_tests()
        self.set_unit_frequencies()

        now = timezone.now().astimezone(timezone.get_current_timezone()).date()

        c = {
            'from_date': now - timezone.timedelta(days=365),
            'to_date': now + timezone.timedelta(days=1),
            'frequencies': models.Frequency.objects.all(),
            'tests': self.tests,
            'test_lists': self.test_lists,
            'categories': models.Category.objects.all(),
            'statuses': models.TestInstanceStatus.objects.all(),
            'units': Unit.objects.values('pk', 'name', 'active'),
            'unit_frequencies': json.dumps(self.unit_frequencies, cls=SetEncoder),
            # 'service_types': sl_models.ServiceType.objects.all(),
            'service_types': {st.id: st.name for st in sl_models.ServiceType.objects.all()},
            'active_unit_test_list': self.get_active_test_lists()
        }
        context.update(c)
        return context

    def get_active_test_lists(self):

        utc_tl_active = models.UnitTestCollection.objects.filter(
            active=True,
            content_type=ContentType.objects.get_for_model(models.TestList)
        )

        to_return = {}
        for utc in utc_tl_active:
            if utc.unit_id not in to_return:
                to_return[utc.unit_id] = [utc.object_id]
            else:
                to_return[utc.unit_id].append(utc.object_id)

        utc_tlc_active = models.UnitTestCollection.objects.filter(
            active=True,
            content_type=ContentType.objects.get_for_model(models.TestListCycle)
        )

        for utc in utc_tlc_active:
            for tlcm in models.TestListCycleMembership.objects.filter(cycle_id=utc.object_id):
                if utc.unit_id not in to_return:
                    to_return[utc.unit_id] = [tlcm.test_list_id]
                else:
                    to_return[utc.unit_id].append(tlcm.test_list_id)

        return to_return

    def set_unit_frequencies(self):

        unit_frequencies = models.UnitTestCollection.objects.exclude(
            last_instance=None
        ).values_list(
            "unit", "frequency"
        ).order_by("unit").distinct()

        self.unit_frequencies = collections.defaultdict(set)
        for u, f in unit_frequencies:
            f = f or 0 # use 0 id for ad hoc frequencies
            self.unit_frequencies[u].add(f)

    def set_test_lists(self):
        """self.test_lists is set to all test lists that have been completed
        one or more times"""

        self.test_lists = models.TestList.objects.order_by(
            "name"
        ).values(
            "pk", "description", "name",
        ).annotate(
            instance_count=Count("testlistinstance"),
        ).filter(
            instance_count__gt=0,
            # testlistmembership__test__chart_visibility=True
        )

    def set_tests(self):
        """self.tests is set to all tests that are chartable"""

        self.tests = models.Test.objects.order_by(
            "name"
        ).filter(
            chart_visibility=True
        ).values(
            "pk", "category", "name", "description",
        )


class BaseChartView(View):
    """
    Base AJAX view responsible for retrieving & tabulating data to be
    plotted for charts.
    """

    def get(self, request):

        self.get_plot_data()
        headers, rows = self.create_data_table()
        resp = self.render_to_response({"plot_data": self.plot_data, "headers": headers, "rows": rows})
        return resp

    def create_data_table(self):
        """
        Take all the :model:`qa.TestInstance`s and tabulate them (grouped by
        unit/test) along with the reference value at the time they were performed.
        """

        headers = []
        max_len = 0
        cols = []

        r = lambda ref: ref if ref is not None else ""

        # collect all data in 'date/value/ref triplets
        for name, data in self.plot_data['series'].items():
            headers.append(name)
            col = [(p["display_date"], p["display"], r(p["orig_reference"])) for p in data['series_data']]
            cols.append(col)
            max_len = max(len(col), max_len)

        # generate table from triplets
        rows = []
        for idx in range(max_len):
            row = []
            for col in cols:
                try:
                    row.append(col[idx])
                except IndexError:
                    row.append(["", "", ""])
            rows.append(row)

        return headers, rows

    def render_table(self, headers, rows):

        context = Context({
            "ncols": 3 * len(rows[0]) if rows else 0,
            "rows": rows,
            "headers": headers
        })
        template = get_template("qa/qa_data_table.html")

        return template.render(context)

    def get_date(self, default_to, default_from):
        """take date from GET data and convert it to utc"""

        # datetime strings coming in will be in local time, make sure they get
        # converted to utc

        try:
            d_from = timezone.datetime.strptime(self.request.GET.get('date_range').split(' - ')[0], settings.SIMPLE_DATE_FORMAT)
        except Exception as e:
            d_from = default_from

        try:
            d_to = timezone.datetime.strptime(self.request.GET.get('date_range').split(' - ')[1], settings.SIMPLE_DATE_FORMAT)
        except:
            d_to = default_to

        if timezone.is_naive(d_to):
            d_to = timezone.make_aware(d_to, timezone.get_current_timezone())
            d_from = timezone.make_aware(d_from, timezone.get_current_timezone())

        return [d_from.astimezone(timezone.utc), d_to.astimezone(timezone.utc)]

    def convert_date(self, date):
        """by default we assume date is being used by javascript, so convert to ISO"""
        return date.isoformat()

    def test_instance_to_point(self, ti, relative=False):
        """Grab relevent plot data from a :model:`qa.TestInstance`"""

        if relative and ti.reference and ti.value is not None:

            ref_is_not_zero = ti.reference.value != 0.
            has_percent_tol = (ti.tolerance and ti.tolerance.type == models.PERCENT)
            has_no_tol = ti.tolerance is None

            use_percent = has_percent_tol or (has_no_tol and ref_is_not_zero)

            if use_percent:

                value = 100 * (ti.value - ti.reference.value) / ti.reference.value
                ref_value = 0.
            else:
                value = ti.value - ti.reference.value
                ref_value = 0
        else:
            value = ti.value
            ref_value = ti.reference.value if ti.reference is not None else None

        point = {
            "act_high": None, "act_low": None, "tol_low": None, "tol_high": None,
            "date": self.convert_date(timezone.make_naive(ti.work_completed, local_tz)),
            "display_date": ti.work_completed,
            "value": value,
            "display": ti.value_display() if not ti.skipped else "",
            "reference": ref_value,
            "orig_reference": ti.reference.value if ti.reference else None,
            'test_instance_id': ti.id,
            'test_list_instance': {'date': ti.test_list_instance.created, 'id': ti.test_list_instance.id}

        }

        if ti.tolerance is not None and ref_value is not None:
            if relative and ti.reference and ti.reference.value != 0. and not ti.tolerance.type == models.ABSOLUTE:
                tols = ti.tolerance.tolerances_for_value(100)
                for k in tols:
                    if tols[k] is not None:
                        tols[k] -= 100.
            else:
                tols = ti.tolerance.tolerances_for_value(ref_value)

            point.update(tols)

        return point

    def get_plot_data(self):
        """Retrieve all :model:`qa.TestInstance` data requested."""

        self.plot_data = {
            'series': {},
            'events': []
        }

        now = timezone.now()
        dates = self.get_date(now, now - timezone.timedelta(days=365))

        from_date = dates[0]
        to_date = dates[1]

        combine_data = self.request.GET.get("combine_data") == "true"
        relative = self.request.GET.get("relative") == "true"

        tests = self.request.GET.getlist("tests[]", [])
        test_lists = self.request.GET.getlist("test_lists[]", [])
        units = self.request.GET.getlist("units[]", [])
        statuses = self.request.GET.getlist("statuses[]", [])

        show_events = self.request.GET.get('show_events') == 'true'
        se_review_required = self.request.GET.get('review_required') == 'true'
        # se_types = self.request.GET.getlist('service_types[]', [])

        if not (tests and test_lists and units and statuses):
            return

        tests = models.Test.objects.filter(pk__in=tests)
        test_lists = models.TestList.objects.filter(pk__in=test_lists)
        units = Unit.objects.filter(pk__in=units)
        statuses = models.TestInstanceStatus.objects.filter(pk__in=statuses)

        # test_list_names = {tl.id: tl.name for tl in test_lists}

        if not combine_data:
            # retrieve test instances for every possible permutation of the
            # requested test list, test & units
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
                    'test_list_instance', 'test_list_instance__test_list'
                ).order_by(
                    "work_completed"
                )
                if tis:
                    # tli = tis.first().test_list_instance
                    name = "%s - %s :: %s%s" % (u.name, tl.name, t.name, " (relative to ref)" if relative else "")
                    self.plot_data['series'][name] = {
                        'series_data': [self.test_instance_to_point(ti, relative=relative) for ti in tis],
                        'unit': {'name': u.name, 'id': u.id},
                        'test_list': {'name': tl.name, 'id': tl.id},
                    }
        else:
            # retrieve test instances for every possible permutation of the
            # requested test & units
            for t, u in itertools.product(tests, units):
                tis = models.TestInstance.objects.filter(
                    unit_test_info__test=t,
                    unit_test_info__unit=u,
                    status__pk__in=statuses,
                    work_completed__gte=from_date,
                    work_completed__lte=to_date,
                ).select_related(
                    "reference", "tolerance", "unit_test_info__test", "unit_test_info__unit", "status", 'test_list_instance'
                ).order_by(
                    "work_completed"
                )
                if tis:
                    tli = tis.first().test_list_instance
                    name = "%s :: %s%s" % (u.name, t.name, " (relative to ref)" if relative else "")
                    self.plot_data['series'][name] = {
                        'series_data': [self.test_instance_to_point(ti, relative=relative) for ti in tis],
                        'unit': {'name': u.name, 'id': u.id},
                        'test_list': {'name': tli.test_list.name, 'id': tli.test_list.id},
                        # 'test_list_instance': {'date': tli.created, 'id': tli.id}
                    }

        if show_events:

            ses = sl_models.ServiceEvent.objects.filter(
                unit_service_area__unit__in=units,
                datetime_service__gte=from_date,
                datetime_service__lte=to_date
            ).select_related(
                'test_list_instance_initiated_by', 'unit_service_area__unit', 'unit_service_area__service_area'
            ).order_by('datetime_service')

            if se_review_required:
                ses = ses.filter(is_review_required=True)

            for se in ses:

                qa_followups = sl_models.QAFollowup.objects.filter(service_event=se).select_related(
                    'test_list_instance', 'test_list_instance__test_list'
                )

                self.plot_data['events'].append({
                    'date': timezone.localtime(se.datetime_service),
                    'id': se.id,
                    'type': se.service_type_id,
                    'is_review_required': se.is_review_required,
                    'initiated_by': se.test_list_instance_initiated_by_id,
                    'followups': [{'id': qaf.id, 'test_list_instance': qaf.test_list_instance_id, 'test_list': qaf.test_list_instance.test_list_id if qaf.test_list_instance else ''} for qaf in qa_followups],
                    'work_description': se.work_description,
                    'problem_description': se.problem_description,
                    'unit': {'id': se.unit_service_area.unit_id, 'name': se.unit_service_area.unit.name},
                    'service_area': {'id': se.unit_service_area.service_area_id, 'name': se.unit_service_area.service_area.name},
                })

        # self.plot_data['test_list_names'] = test_list_names

    def render_to_response(self, context):
        context['table'] = self.render_table(context['headers'], context['rows'])
        return self.render_json_response(context)


class BasicChartData(PermissionRequiredMixin, JSONResponseMixin, BaseChartView):
    """JSON view used for basic chart type"""

    permission_required = "qa.can_view_charts"
    raise_exception = True


class ControlChartImage(PermissionRequiredMixin, BaseChartView):
    """Return a control chart image from given qa data"""

    permission_required = "qa.can_view_charts"
    raise_exception = True

    def convert_date(self, dt):
        """date is being used by Python code, so no need to convert to ISO"""
        return dt

    def get_number_from_request(self, param, default, dtype=float):
        """look for a number in GET and convert it to the given datatype"""
        try:
            v = dtype(self.request.GET.get(param, default))
        except:
            v = default
        return v

    def get_plot_data(self):
        """
        The control chart software can only handle one test at a time
        so if user requested more than one test, just grab
        one of them.
        """

        super(ControlChartImage, self).get_plot_data()

        if self.plot_data:
            self.plot_data = dict([self.plot_data.popitem()])

    def render_to_response(self, context):
        """Create a png image and write the control chart image to it"""

        fig = Figure(dpi=72, facecolor="white")
        dpi = fig.get_dpi()
        fig.set_size_inches(
            self.get_number_from_request("width", 700) / dpi,
            self.get_number_from_request("height", 480) / dpi,
        )
        canvas = FigureCanvas(fig)
        dates, data = [], []

        if context["data"] and list(context["data"].values()):
            name, points = list(context["data"].items())[0]
            if points:
                dates, data = list(zip(*[(ti["date"], ti["value"]) for ti in points]))

        n_baseline_subgroups = self.get_number_from_request("n_baseline_subgroups", 2, dtype=int)
        n_baseline_subgroups = max(2, n_baseline_subgroups)

        subgroup_size = self.get_number_from_request("subgroup_size", 2, dtype=int)
        if not (1 < subgroup_size < 100):
            subgroup_size = 1

        include_fit = self.request.GET.get("fit_data", "") == "true"

        response = HttpResponse(content_type="image/png")
        if n_baseline_subgroups < 1 or n_baseline_subgroups > len(data) / subgroup_size:
            fig.text(0.1, 0.9, "Not enough data for control chart", fontsize=20)
            canvas.print_png(response)
        else:
            try:
                control_chart.display(fig, numpy.array(data), subgroup_size, n_baseline_subgroups, fit=include_fit, dates=dates)
                fig.autofmt_xdate()
                canvas.print_png(response)
            except (RuntimeError, OverflowError, TypeError) as e:  # pragma: nocover
                fig.clf()
                msg = "There was a problem generating your control chart:\n%s" % str(e)
                fig.text(0.1, 0.9, "\n".join(textwrap.wrap(msg, 40)), fontsize=12)
                canvas.print_png(response)

        return response


class ExportCSVView(PermissionRequiredMixin, JSONResponseMixin, BaseChartView):
    """JSON view used for basic chart type"""

    permission_required = "qa.can_view_charts"
    raise_exception = True

    def render_to_response(self, context):
        import csv
        from django.utils import formats
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="qatrackexport.csv"'

        writer = csv.writer(response)
        header1 = []
        header2 = []
        for h in context['headers']:
            header1.extend([h.encode('utf-8'), '', ''])
            header2.extend(["Date", "Value", "Ref"])

        writer.writerow(header1)
        writer.writerow(header2)

        for row_set in context['rows']:
            row = []
            for date, val, ref in row_set:
                date = formats.date_format(date, "DATETIME_FORMAT") if date is not "" else ""
                row.extend([date, val, ref])
            writer.writerow(row)

        return response
