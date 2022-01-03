import calendar
import glob
import json
import os
import random

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.sites.shortcuts import get_current_site
from django.core.files.uploadedfile import SimpleUploadedFile
import django.forms
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from django_comments.models import Comment
from freezegun import freeze_time

from qatrack.attachments.models import Attachment
from qatrack.qa import models, trees, views
from qatrack.qa.views import forms
import qatrack.qa.views.base
import qatrack.qa.views.charts
import qatrack.qa.views.perform
import qatrack.qa.views.review
from qatrack.qatrack_core.dates import format_as_date
import qatrack.units.models as umodels
from qatrack.units.tests import utils as u_utils

from . import utils

logger = qatrack.qa.views.base.logger


class MockUser(object):

    def has_perm(self, *args):
        return True


superuser = MockUser()


class TestURLS(TestCase):
    """just test urls to make sure at the very least they are valid and return 200"""

    def setUp(self):
        u = utils.create_user()
        self.client.login(username="user", password="password")
        g = utils.create_group()
        u.groups.add(g)
        u.save()

    def returns_200(self, url, method="get"):
        return getattr(self.client, method)(url).status_code == 200

    def test_qa_redirect(self):
        resp = self.client.get("/qa/")
        assert resp.url == '/qc/'

    def test_qa_urls(self):

        utils.create_category()
        utils.create_status()
        u1 = u_utils.create_unit(number=1, name="u1")
        u_utils.create_unit(
            number=2,
            name="u2",
        )
        utc = utils.create_unit_test_collection(unit=u1)
        tli = utils.create_test_list_instance(unit_test_collection=utc)

        url_names = (
            ("home", {}),
            ("all_lists", {}),
            ("charts", {}),
            ("chart_data", {}),
            ("control_chart", {}),
            ("overview", {}),
            ("overview_due_dates", {}),
            ("review_all", {}),
            ("review_utc", {"pk": "%d" % utc.pk}),
            ("choose_review_frequency", {}),
            ("review_by_frequency", {"frequency": "daily/monthly/ad-hoc"}),
            ("choose_review_unit", {}),
            ("review_by_unit", {"unit_number": "1"}),
            ("review_by_unit", {"unit_number": "1/2"}),
            ("complete_instances", {}),
            ("review_test_list_instance", {"pk": "%d" % tli.pk}),
            ("unreviewed", {}),
            ("in_progress", {}),
            ("edit_tli", {"pk": "%d" % (tli.pk)}),
            ("choose_unit", {}),
            ("perform_qa", {"pk": "%d" % utc.pk}),
            ("qa_by_unit", {"unit_number": "1"}),
            ("qa_by_frequency", {"frequency": "daily/ad-hoc"}),
            ("qa_by_unit_frequency", {"unit_number": "1", "frequency": "daily/ad-hoc"}),
            ("groups-app", {}),
        )  # YAPF:disable

        for url, kwargs in url_names:
            logger.info("\t > testing: " + url)
            self.assertTrue(self.returns_200(reverse(url, kwargs=kwargs)))

    def test_login(self):
        self.assertTrue(self.returns_200(settings.LOGIN_URL))

    def test_login_redirect(self):
        self.assertTrue(self.returns_200(settings.LOGIN_REDIRECT_URL))

    def test_perform(self):
        utils.create_status()
        utc = utils.create_unit_test_collection()
        url = reverse("perform_qa", kwargs={"pk": "%d" % utc.pk})
        self.assertTrue(self.returns_200(url))
        url = reverse("perform_qa", kwargs={"pk": "2"})

        self.assertTrue(404 == self.client.get(url).status_code)

    def test_utc_fail(self):
        utils.create_status()
        url = reverse("review_utc", kwargs={"pk": 9999})
        self.assertEqual(self.client.get(url).status_code, 404)


class TestControlImage(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.view = views.charts.ControlChartImage.as_view()
        self.url = reverse("control_chart")

    def tearDown(self):
        models.TestListInstance.objects.all().delete()
        models.UnitTestInfo.objects.all().delete()
        models.Test.objects.all().delete()
        models.TestList.objects.all().delete()
        models.Unit.objects.all().delete()

    def test_not_enough_data(self):
        request = self.factory.get(self.url)
        request.user = superuser
        response = self.view(request)

        self.assertTrue(response.get("content-type"), "image/png")

    def test_baseline_subgroups(self):

        tl = utils.create_test_list()
        test = utils.create_test()
        unit = u_utils.create_unit()
        utils.create_unit_test_info(test=test, unit=unit)

        utils.create_status()
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        tomorrow = yesterday + timezone.timedelta(days=2)

        for n in [-1, 0, 1, 2, "nonnumber"]:
            url = self.make_url(test.pk, tl.pk, unit.pk, yesterday, tomorrow, n_base=n)
            request = self.factory.get(url)
            request.user = superuser
            response = self.view(request)
            self.assertTrue(response.get("content-type"), "image/png")

    def test_invalid_subgroup_size(self):
        tl = utils.create_test_list()
        test = utils.create_test()
        unit = u_utils.create_unit()
        utils.create_unit_test_info(test=test, unit=unit)

        utils.create_status()
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        tomorrow = yesterday + timezone.timedelta(days=2)

        for n in [-1, 0, 101, "nonnumber"]:
            url = self.make_url(test.pk, tl.pk, unit.pk, yesterday, tomorrow, sg_size=n)
            request = self.factory.get(url)
            request.user = superuser
            response = self.view(request)
            self.assertTrue(response.get("content-type"), "image/png")

    def test_include_fit(self):
        for f in ["true", "false"]:
            request = self.factory.get(self.url + "?fit_data=%s" % f)
            request.user = superuser
            response = self.view(request)
            self.assertTrue(response.get("content-type"), "image/png")

    def make_url(self, pk, tl_pk, upk, from_date, to_date, sg_size=2, n_base=2, fit="true"):
        url = self.url + "?subgroup_size=%s&n_baseline_subgroups=%s&fit_data=%s" % (sg_size, n_base, fit)
        url += "&tests[]=%s" % pk
        url += "&test_lists[]=%s" % tl_pk
        url += "&units[]=%s" % upk
        url += "&statuses[]=%s" % models.ReviewStatus.objects.all()[0].pk
        url += "&from_date=%s" % format_as_date(from_date)
        url += "&to_date=%s" % format_as_date(to_date)
        return url

    def test_valid(self):
        tl = utils.create_test_list()
        test = utils.create_test()
        utils.create_test_list_membership(tl, test)
        unit = u_utils.create_unit()
        utc = utils.create_unit_test_collection(test_collection=tl, unit=unit)
        uti = models.UnitTestInfo.objects.get(test=test, unit=unit)

        status = utils.create_status()

        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        tomorrow = yesterday + timezone.timedelta(days=2)
        url = self.make_url(test.pk, tl.pk, unit.pk, yesterday, tomorrow)

        for n in (1, 1, 8, 90):
            for x in range(n):
                tli = utils.create_test_list_instance(unit_test_collection=utc, status=status)
                utils.create_test_instance(
                    tli,
                    unit_test_info=uti,
                    value=random.gauss(1, 0.5),
                )

            request = self.factory.get(url)
            request.user = superuser
            response = self.view(request)
            self.assertTrue(response.get("content-type"), "image/png")

    def test_invalid(self):
        tl = utils.create_test_list()
        test = utils.create_test()
        unit = u_utils.create_unit()
        uti = utils.create_unit_test_info(test=test, unit=unit)
        utc = utils.create_unit_test_collection(test_collection=tl, unit=unit)

        status = utils.create_status()
        tli = utils.create_test_list_instance(unit_test_collection=utc, status=status)

        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        tomorrow = yesterday + timezone.timedelta(days=2)

        url = self.make_url(test.pk, tl.pk, unit.pk, yesterday, yesterday)
        request = self.factory.get(url)
        request.user = superuser
        response = self.view(request)
        self.assertTrue(response.get("content-type"), "image/png")

        url = self.make_url(test.pk, tl.pk, unit.pk, yesterday, tomorrow, fit="true")

        # generate some data that the control chart fit function won't be able to fit
        for x in range(10):
            utils.create_test_instance(tli, value=x, unit_test_info=uti)

        request = self.factory.get(url)
        request.user = superuser
        response = self.view(request)
        self.assertTrue(response.get("content-type"), "image/png")

    def test_fails(self):
        tl = utils.create_test_list()
        test = utils.create_test()
        unit = u_utils.create_unit()
        uti = utils.create_unit_test_info(test=test, unit=unit)
        utc = utils.create_unit_test_collection(test_collection=tl, unit=unit)

        status = utils.create_status()
        tli = utils.create_test_list_instance(unit_test_collection=utc, status=status)

        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        tomorrow = yesterday + timezone.timedelta(days=2)

        url = self.make_url(test.pk, tl.pk, unit.pk, yesterday, yesterday)
        request = self.factory.get(url)
        request.user = superuser
        response = self.view(request)
        self.assertTrue(response.get("content-type"), "image/png")

        url = self.make_url(test.pk, tl.pk, unit.pk, yesterday, tomorrow, fit="true")
        import qatrack.qa.control_chart
        old_display = qatrack.qa.control_chart.control_chart.display

        def mock_display(*args, **kwargs):
            raise RuntimeError("test")

        qatrack.qa.control_chart.control_chart.display = mock_display
        # generate some data that the control chart fit function won't be able to fit
        for x in range(10):
            utils.create_test_instance(tli, value=x, unit_test_info=uti)

        request = self.factory.get(url)
        request.user = superuser
        response = self.view(request)
        self.assertTrue(response.get("content-type"), "image/png")
        qatrack.qa.control_chart.control_chart.display = old_display


class TestChartView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        freq = utils.create_frequency()

        self.tls = []
        self.units = []
        self.tests = []
        for i in range(1, 3):
            unit = u_utils.create_unit(number=i)
            self.units.append(unit)
            tl = utils.create_test_list(name="tl%s" % i)
            self.tls.append(tl)
            test = utils.create_test(name="test%s" % i)
            self.tests.append(test)
            utils.create_test_list_membership(tl, test)
            utils.create_unit_test_collection(unit=unit, test_collection=tl, frequency=freq)

    def test_get_test_lists_for_unit_frequencies_all(self):

        url = reverse("charts_testlists")
        request = self.factory.get(url)
        response = qatrack.qa.views.charts.get_test_lists_for_unit_frequencies(request)
        values = json.loads(response.content.decode("UTF-8"))
        expected = {tl.pk for tl in self.tls}
        assert expected == set(values['test_lists'])

    def test_get_test_lists_for_unit_frequencies_filtered(self):

        url = reverse("charts_testlists") + "?units[]=%d" % (self.units[0].pk)
        request = self.factory.get(url)
        response = qatrack.qa.views.charts.get_test_lists_for_unit_frequencies(request)
        values = json.loads(response.content.decode("UTF-8"))
        expected = {"test_lists": [self.tls[0].pk]}
        self.assertDictEqual(values, expected)

    def test_get_tests_for_test_lists_all(self):

        url = reverse("charts_tests")
        request = self.factory.get(url)
        response = qatrack.qa.views.charts.get_tests_for_test_lists(request)
        values = json.loads(response.content.decode("UTF-8"))
        expected = {"tests": [t.pk for t in self.tests]}
        self.assertDictEqual(values, expected)

    def test_get_tests_for_test_lists_filtered(self):

        url = reverse("charts_tests") + "?test_lists[]=%d" % (self.tls[0].pk)
        request = self.factory.get(url)
        response = qatrack.qa.views.charts.get_tests_for_test_lists(request)
        values = json.loads(response.content.decode("UTF-8"))
        expected = {"tests": [self.tests[0].pk]}
        self.assertDictEqual(values, expected)

    def test_instance_to_point_relative_with_none_tol(self):

        ref = qatrack.qa.models.Reference(value=100)
        tol = utils.create_tolerance(tol_type=models.PERCENT, tol_low=None, tol_high=None)
        ti = qatrack.qa.models.TestInstance(reference=ref, tolerance=tol, value=100)
        ti.unit_test_info = models.UnitTestInfo.objects.first()
        ti.test_list_instance = qatrack.qa.models.TestListInstance()
        ti.value_display = lambda: str(ti.value)
        view = views.charts.BaseChartView()
        point = view.test_instance_to_point(ti, relative=True)
        self.assertIsNone(point['tol_low'])

    def test_instance_to_point_relative_360(self):
        """Three sixty test, relative to ref with value 359 should result in value of -1"""
        test = utils.create_test(name="360", test_type=models.WRAPAROUND, wrap_high=360, wrap_low=0)
        ref = qatrack.qa.models.Reference(value=0)
        tol = utils.create_tolerance(tol_type=models.PERCENT, tol_low=None, tol_high=None)
        ti = qatrack.qa.models.TestInstance(reference=ref, tolerance=tol, value=359)
        ti.unit_test_info = models.UnitTestInfo.objects.create(test=test, unit=self.units[0])
        ti.test_list_instance = qatrack.qa.models.TestListInstance()
        ti.value_display = lambda: str(ti.value)
        view = views.charts.BaseChartView()
        point = view.test_instance_to_point(ti, relative=True)
        assert point['value'] == -1

    def test_instance_to_point_relative_m360(self):
        """Three sixty test, relative to ref with value -359 should result in value of 1"""
        test = utils.create_test(name="360", test_type=models.WRAPAROUND, wrap_high=360, wrap_low=0)
        ref = qatrack.qa.models.Reference(value=0)
        tol = utils.create_tolerance(tol_type=models.PERCENT, tol_low=None, tol_high=None)
        ti = qatrack.qa.models.TestInstance(reference=ref, tolerance=tol, value=-359)
        ti.unit_test_info = models.UnitTestInfo.objects.create(test=test, unit=self.units[0])
        ti.test_list_instance = qatrack.qa.models.TestListInstance()
        ti.value_display = lambda: str(ti.value)
        view = views.charts.BaseChartView()
        point = view.test_instance_to_point(ti, relative=True)
        assert point['value'] == 1

    def test_instance_to_point_relative_m1(self):
        """Three sixty test, relative to ref with value -1 should result in value of -1"""
        test = utils.create_test(name="360", test_type=models.WRAPAROUND, wrap_high=360, wrap_low=0)
        ref = qatrack.qa.models.Reference(value=0)
        tol = utils.create_tolerance(tol_type=models.PERCENT, tol_low=None, tol_high=None)
        ti = qatrack.qa.models.TestInstance(reference=ref, tolerance=tol, value=-1)
        ti.unit_test_info = models.UnitTestInfo.objects.create(test=test, unit=self.units[0])
        ti.test_list_instance = qatrack.qa.models.TestListInstance()
        ti.value_display = lambda: str(ti.value)
        view = views.charts.BaseChartView()
        point = view.test_instance_to_point(ti, relative=True)
        assert point['value'] == -1


class TestChartData(TestCase):

    def setUp(self):
        self.url = reverse("chart_data")
        self.view = views.charts.BasicChartData.as_view()

        self.status = utils.create_status()
        ref = utils.create_reference(value=1.)
        tol = utils.create_tolerance(tol_type=models.ABSOLUTE)
        per_tol = utils.create_tolerance(tol_type=models.PERCENT)
        self.test1 = utils.create_test(name="test1")
        self.test2 = utils.create_test(name="test2")
        self.tl1 = utils.create_test_list(name="tl1")
        self.tl2 = utils.create_test_list(name="tl2")

        utils.create_test_list_membership(self.tl1, self.test1)
        utils.create_test_list_membership(self.tl2, self.test2)
        utils.create_test_list_membership(self.tl2, self.test1)

        self.utc1 = utils.create_unit_test_collection(test_collection=self.tl1)
        self.utc2 = utils.create_unit_test_collection(
            unit=self.utc1.unit, test_collection=self.tl2, frequency=self.utc1.frequency
        )

        self.uti1 = models.UnitTestInfo.objects.get(test=self.test1)
        self.uti1.reference = ref
        self.uti1.tolerance = tol
        self.uti1.save()

        self.uti2 = models.UnitTestInfo.objects.get(test=self.test2)
        self.uti2.references = ref
        self.uti2.tolerance = per_tol
        self.uti2.save()

        self.NPOINTS = 10
        for x in range(self.NPOINTS):
            tli = utils.create_test_list_instance(unit_test_collection=self.utc1, status=self.status)
            ti = utils.create_test_instance(
                value=1., unit_test_info=self.uti1, test_list_instance=tli
            )
            ti.reference = ref
            ti.tolerance = tol
            ti.save()

            tli2 = utils.create_test_list_instance(unit_test_collection=self.utc2, status=self.status)
            ti2 = utils.create_test_instance(
                value=1., unit_test_info=self.uti1, test_list_instance=tli2
            )
            ti2.reference = ref
            ti2.tolerance = per_tol
            ti2.save()

            if x < self.NPOINTS // 2:
                # create less points for one tests to ensure tabulation routines
                # can handle data sets of different lengths
                tli2 = utils.create_test_list_instance(unit_test_collection=self.utc2, status=self.status)
                ti2 = utils.create_test_instance(
                    value=1.5, unit_test_info=self.uti2, test_list_instance=tli2
                )
                ti2.reference = ref
                ti2.tolerance = per_tol
                ti2.save()

        self.client.login(username="user", password="password")

    def test_basic_data(self):
        data = {
            "tests[]": [self.test1.pk, self.test2.pk],
            "test_lists[]": [self.tl1.pk, self.tl2.pk],
            "units[]": [self.utc1.unit.pk],
            "statuses[]": [self.status.pk],
        }
        resp = self.client.get(self.url, data=data)
        data = json.loads(resp.content.decode("UTF-8"))
        expected = [1.] * self.NPOINTS
        unit_name = self.utc1.unit.name
        tli_name = self.tl1.name
        actual = [
            x['value'] for x in data['plot_data']['series']['%s - %s :: test1' % (unit_name, tli_name)]['series_data']
        ]
        self.assertListEqual(actual, expected)

    def test_basic_data_relative(self):
        data = {
            "tests[]": [self.test1.pk, self.test2.pk],
            "test_lists[]": [self.tl1.pk, self.tl2.pk],
            "units[]": [self.utc1.unit.pk],
            "statuses[]": [self.status.pk],
            "relative": "true",
        }
        resp = self.client.get(self.url, data=data)
        data = json.loads(resp.content.decode("UTF-8"))
        expected = [50.] * (self.NPOINTS // 2)
        unit_name = self.utc1.unit.name
        tl2_name = self.tl2.name
        actual = [
            x['value']
            for x in data['plot_data']['series']['%s - %s :: test2 (relative to ref)' % (unit_name,
                                                                                         tl2_name)]['series_data']
        ]
        self.assertListEqual(actual, expected)

    def test_basic_data_combined(self):
        data = {
            "tests[]": [self.test1.pk, self.test2.pk],
            "test_lists[]": [self.tl1.pk, self.tl2.pk],
            "units[]": [self.utc1.unit.pk],
            "statuses[]": [self.status.pk],
            "combine_data": "true"
        }
        resp = self.client.get(self.url, data=data)
        data = json.loads(resp.content.decode("UTF-8"))
        expected = [1.] * (2 * self.NPOINTS)
        unit_name = self.utc1.unit.name
        actual = [x['value'] for x in data['plot_data']['series']['%s :: test1' % unit_name]['series_data']]
        self.assertListEqual(actual, expected)

    def test_export_csv_view(self):
        url = reverse("charts_export_csv")
        data = {
            "tests[]": [self.test1.pk, self.test2.pk],
            "test_lists[]": [self.tl1.pk, self.tl2.pk],
            "units[]": [self.utc1.unit.pk],
            "statuses[]": [self.status.pk],
            "relative": "true",
        }
        resp = self.client.get(url, data=data)
        expected_nlines = 2 + 10 + 1  # 2 header  + 10 rows data + 1 blank
        self.assertTrue(len(resp.content.decode("UTF-8").split('\n')), expected_nlines)

        self.assertEqual(resp.get('Content-Disposition'), 'attachment; filename="qatrackexport.csv"')


class TestComposite(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.view = views.perform.CompositeCalculation.as_view()
        self.url = reverse("composite")

        self.user = utils.create_user()
        self.unit = u_utils.create_unit()
        self.test_list = utils.create_test_list()
        self.t1 = utils.create_test(name="test1")
        self.t2 = utils.create_test(name="test2")
        self.tc = utils.create_test(name="testc", test_type=models.COMPOSITE)
        self.tc.calculation_procedure = "result = test1 + test2"
        self.tc.save()
        for t in [self.t1, self.t2, self.tc]:
            utils.create_test_list_membership(self.test_list, t)
            utils.create_unit_test_info(test=t, unit=self.unit)

    @override_settings(CONSTANT_PRECISION=2)
    def test_composite(self):

        data = {
            'tests': {
                "testc": "",
                "test1": 1,
                "test2": 2
            },
            'meta': {},
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
            'skips': {
                'testc': False,
                'test1': False,
                'test2': False,
            },
        }
        request = self.factory.post(self.url, content_type='application/json', data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {
            "errors": [],
            "results": {
                "testc": {
                    "value": 3.0,
                    "formatted": "3.0",
                    "error": None,
                    "user_attached": [],
                    "comment": None,
                },
            },
            'skips': {},
            "success": True
        }
        self.assertDictEqual(values, expected)

    @override_settings(CONSTANT_PRECISION=2)
    def test_date_composite(self):

        td1 = utils.create_test(name="test_date_1", test_type=models.DATE)
        td2 = utils.create_test(name="test_date_2", test_type=models.DATETIME)
        tcd = utils.create_test(name="test_date_c", test_type=models.COMPOSITE)
        tcd.calculation_procedure = "result = (test_date_2.date() - test_date_1).total_seconds()"
        tcd.save()
        for t in [td1, td2, tcd]:
            utils.create_test_list_membership(self.test_list, t)
            utils.create_unit_test_info(test=t, unit=self.unit)

        data = {
            'tests': {
                "testc": "",
                "test1": 1,
                "test2": 2,
                "test_date_1": "2019-08-01",
                "test_date_2": "2019-08-02 23:45:00",
            },
            'meta': {},
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
        }
        request = self.factory.post(self.url, content_type='application/json', data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {
            "errors": [],
            "results": {
                "testc": {
                    "value": 3.0,
                    "formatted": "3.0",
                    "error": None,
                    "user_attached": [],
                    "comment": None,
                },
                "test_date_c": {
                    "value": 24 * 60 * 60,
                    "formatted": "8.6e+4",
                    "error": None,
                    "user_attached": [],
                    "comment": None,
                },
            },
            "skips": {},
            "success": True
        }
        self.assertDictEqual(values, expected)

    def test_composite_with_formatting(self):

        self.tc.formatting = "%.3E"
        self.tc.save()

        data = {
            'tests': {
                "testc": "",
                "test1": 100,
                "test2": 200,
            },
            'meta': {},
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
        }
        request = self.factory.post(self.url, content_type='application/json', data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {
            "errors": [],
            "results": {
                "testc": {
                    "value": 300,
                    "formatted": "3.000E+02",
                    "error": None,
                    "user_attached": [],
                    "comment": None,
                },
            },
            "skips": {},
            "success": True,
        }
        self.assertDictEqual(values, expected)

    def test_composite_of_composite(self):

        tcc = utils.create_test(name="testcc", test_type=models.COMPOSITE)
        tcc.calculation_procedure = "result = 2*testc"
        tcc.save()
        utils.create_test_list_membership(self.test_list, tcc)
        utils.create_unit_test_info(test=tcc, unit=self.unit)
        data = {
            'tests': {
                "testc": "",
                "testcc": "",
                "test1": 1.,
                "test2": 2.,
            },
            'meta': {},
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
        }
        request = self.factory.post(self.url, content_type='application/json', data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {
            "errors": [],
            "results": {
                "testc": {
                    "value": 3.0,
                    "formatted": '3.0000000',
                    "error": None,
                    "user_attached": [],
                    "comment": None,
                },
                "testcc": {
                    "value": 6.0,
                    "formatted": '6.0000000',
                    "error": None,
                    "user_attached": [],
                    "comment": None,
                },
            },
            'skips': {},
            "success": True
        }
        self.assertDictEqual(values, expected)

    def test_set_skip(self):

        ts = utils.create_test(name="test_skip", test_type=models.COMPOSITE)
        ts.calculation_procedure = "UTILS.set_skip('test1', True)\nUTILS.set_skip('test2', False)\nresult = 1"
        ts.save()
        utils.create_test_list_membership(self.test_list, ts)
        utils.create_unit_test_info(test=ts, unit=self.unit)
        data = {
            'tests': {
                "testc": "",
                "test_skip": "",
                "test1": 1.,
                "test2": 2.,
            },
            'meta': {},
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
            'skips': {
                'test_skip': False,
                'testc': False,
                'test1': False,
                'test2': True,
            },
        }
        request = self.factory.post(self.url, content_type='application/json', data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {
            "errors": [],
            "results": {
                "testc": {
                    "value": 3.0,
                    "formatted": '3.0000000',
                    "error": None,
                    "user_attached": [],
                    "comment": None,
                },
                "test_skip": {
                    "value": 1.0,
                    "formatted": '1.0000000',
                    "error": None,
                    "user_attached": [],
                    "comment": None,
                },
            },
            'skips': {
                'test1': True,
                'test2': False,
            },
            "success": True,
        }
        self.assertDictEqual(values, expected)

    def test_invalid_values(self):

        data = {
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
            'meta': {},
        }

        request = self.factory.post(self.url, content_type="application/json", data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {"errors": ['Invalid QC Values'], "success": False}
        self.assertDictEqual(values, expected)

    def test_invalid_number(self):

        data = {
            'tests': {
                "testc": {
                    "name": "testc",
                    "current_value": ""
                },
                "test1": {
                    "name": "test1",
                    "current_value": 1
                },
                "test2": {
                    "name": "test2",
                    "current_value": "abc"
                }
            },
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
            'meta': {},
        }

        request = self.factory.post(self.url, content_type="application/json", data=json.dumps(data))
        request.user = self.user
        response = self.view(request)

        values = json.loads(response.content.decode("UTF-8"))

        expected = {
            'errors': [],
            'results': {
                'testc': {
                    'error': (
                        'Invalid Test Procedure: testc", line 1, in '
                        'testc\n'
                        'TypeError: unsupported operand type(s) for +: '
                        "'dict' and 'dict'\n"
                    ),
                    'user_attached': [],
                    "comment": "",
                    'value': None
                },
            },
            "skips": {},
            'success': True
        }
        self.assertDictEqual(values, expected)

    def test_missing_test_list_id(self):
        request = self.factory.post(self.url, content_type="application/json", data=json.dumps({}))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))
        expected = {"errors": ["Invalid or missing test_list_id"], "success": False}
        self.assertDictEqual(values, expected)

    def test_missing_unit_id(self):
        data = {'test_list_id': self.test_list.id}
        request = self.factory.post(self.url, content_type="application/json", data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))
        expected = {"errors": ["Invalid or missing unit_id"], "success": False}
        self.assertDictEqual(values, expected)

    def test_invalid_composite(self):

        self.tc.unittestinfo_set.all().delete()
        self.tc.delete()
        data = {
            'tests': {
                "test1": 1,
                "test2": "abc"
            },
            'meta': '{}',
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
        }

        request = self.factory.post(self.url, content_type="application/json", data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {"errors": ["No Valid Composite ID's"], "success": False}
        self.assertDictEqual(values, expected)

    def test_no_composite(self):

        self.tc.unittestinfo_set.all().delete()
        self.tc.delete()
        data = {
            'tests': {
                "test1": 1,
                "test2": 2
            },
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
            'meta': '{}',
        }

        request = self.factory.post(self.url, content_type="application/json", data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {"errors": ["No Valid Composite ID's"], "success": False}
        self.assertDictEqual(values, expected)

    def test_invalid_json(self):

        data = '{"tests": {"testc"}, u"meta": {}, }'

        request = self.factory.post(self.url, content_type="application/json", data=data)
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        self.assertEqual(values["success"], False)

    def test_invalid_test(self):

        self.tc.calculation_procedure = "foo"
        self.tc.save()

        data = {
            'tests': {
                "testc": "",
                "test1": 1,
                "test2": 2
            },
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
            'meta': {},
        }

        request = self.factory.post(self.url, content_type="application/json", data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {
            'errors': [],
            'results': {
                'testc': {
                    'error': (
                        'Invalid Test Procedure: testc", line 1, in '
                        'testc\n'
                        "NameError: name 'foo' is not defined\n"
                    ),
                    'user_attached': [],
                    "comment": "",
                    'value': None,
                },
            },
            "skips": {},
            'success': True
        }
        self.assertDictEqual(values, expected)

    @override_settings(CONSTANT_PRECISION=2)
    def test_cyclic(self):

        self.cyclic1 = utils.create_test(name="cyclic1", test_type=models.COMPOSITE)
        self.cyclic1.calculation_procedure = "result = cyclic2 + test2"
        self.cyclic1.save()

        self.cyclic2 = utils.create_test(name="cyclic2", test_type=models.COMPOSITE)
        self.cyclic2.calculation_procedure = "result = cyclic1 + test1"
        self.cyclic2.save()
        utils.create_test_list_membership(self.test_list, self.cyclic1)
        utils.create_test_list_membership(self.test_list, self.cyclic2)

        data = {
            'tests': {
                "testc": "",
                "cyclic1": "",
                "cyclic2": "",
                "test1": 1,
                "test2": 2
            },
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
            'meta': {},
        }

        request = self.factory.post(self.url, content_type="application/json", data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        values = json.loads(response.content.decode("UTF-8"))

        expected = {
            'errors': [],
            'results': {
                'cyclic1': {
                    'error': 'Cyclic test dependency',
                    'value': None
                },
                'cyclic2': {
                    'error': 'Cyclic test dependency',
                    'value': None
                },
                'testc': {
                    'error': None,
                    'value': 3,
                    'formatted': "3.0",
                    "user_attached": [],
                    "comment": None,
                }
            },
            "skips": {},
            'success': True,
        }
        self.assertDictEqual(values, expected)


class TestPerformQA(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.view = views.perform.PerformQA.as_view()
        self.status = utils.create_status()

        self.test_list = utils.create_test_list()

        self.t_simple = utils.create_test(name="test_simple")

        self.t_const = utils.create_test(name="test_const", test_type=models.CONSTANT)
        self.t_const.constant_value = 1
        self.t_const.save()

        self.t_comp = utils.create_test(name="test_comp", test_type=models.COMPOSITE)
        self.t_comp.calculation_procedure = "result = test_simple + test_const"
        self.t_comp.save()

        self.t_mult = utils.create_test(name="test_mult", test_type=models.MULTIPLE_CHOICE)
        self.t_mult.choices = "c1,c2,c3"
        self.t_mult.save()

        self.t_bool = utils.create_test(name="test_bool", test_type=models.BOOLEAN)
        self.t_bool.save()

        self.t_string = utils.create_test(name="test string", test_type=models.STRING)
        self.t_string.save()

        self.t_string_comp = utils.create_test(name="test string comp", test_type=models.STRING_COMPOSITE)
        self.t_string_comp.calculation_procedure = "result = 'test'"
        self.t_string_comp.save()

        self.t_upload = utils.create_test(name="test upload", test_type=models.UPLOAD)
        self.t_upload.save()
        self.filename = "TESTRUNNER.tmp"
        self.filepath = os.path.join(settings.TMP_UPLOAD_ROOT, self.filename)

        with open(self.filepath, "w") as f:
            f.write("")

        self.tests = [
            self.t_simple, self.t_const, self.t_comp, self.t_mult, self.t_bool, self.t_string, self.t_upload,
            self.t_string_comp
        ]

        for idx, test in enumerate(self.tests):
            utils.create_test_list_membership(self.test_list, test, idx)

        group = Group(name="foo")
        group.save()

        self.frequency = utils.create_frequency(name="daily")
        self.unit_test_list = utils.create_unit_test_collection(
            test_collection=self.test_list,
            frequency=self.frequency,
        )

        self.unit_test_infos = []
        for test in self.tests:
            self.unit_test_infos.append(models.UnitTestInfo.objects.get(test=test, unit=self.unit_test_list.unit))
        self.url = reverse("perform_qa", kwargs={"pk": self.unit_test_list.pk})
        self.client.login(username="user", password="password")
        self.user = User.objects.get(username="user")
        self.user.is_superuser = False
        self.user.save()
        self.user.groups.add(group)
        self.user.save()

    def tearDown(self):
        for f in glob.glob(os.path.join(settings.MEDIA_ROOT, "*", "TESTRUNNER*")):
            os.remove(f)

    def test_test_forms_present(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["formset"].forms), len(self.tests))

    def test_test_initial_constant(self):
        response = self.client.get(self.url)

        self.assertEqual(
            float(response.context["formset"].forms[self.tests.index(self.t_const)].initial["value"]),
            self.t_const.constant_value
        )

    def test_readonly(self):
        response = self.client.get(self.url)
        readonly = [self.t_comp, self.t_const, self.t_string_comp]

        idxs = [self.tests.index(t) for t in readonly]
        for idx in idxs:
            if not self.tests[idx].type == models.STRING_COMPOSITE:
                self.assertEqual(
                    response.context["formset"].forms[idx].fields["value"].widget.attrs["readonly"], "readonly"
                )
            else:
                self.assertEqual(
                    response.context["formset"].forms[idx].fields["string_value"].widget.attrs["readonly"], "readonly"
                )

    def test_bool_widget(self):
        response = self.client.get(self.url)
        idx = self.tests.index(self.t_bool)
        widget = response.context["formset"].forms[idx].fields["value"].widget

        self.assertIsInstance(widget, django.forms.RadioSelect)
        self.assertEqual(widget.choices, forms.BOOL_CHOICES)

    def test_mult_choice_widget(self):
        response = self.client.get(self.url)
        idx = self.tests.index(self.t_mult)
        widget = response.context["formset"].forms[idx].fields["string_value"].widget

        self.assertTrue(isinstance(widget, django.forms.Select))
        self.assertEqual(widget.choices, [('', ''), ('c1', 'c1'), ('c2', 'c2'), ('c3', 'c3')])

    def test_perform_in_progress(self):
        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
            "in_progress": True,
        }
        self.set_form_data(data)

        response = self.client.post(self.url, data=data)

        self.assertTrue(1, models.TestListInstance.objects.in_progress().count())
        self.assertTrue(len(self.tests), models.TestInstance.objects.in_progress().count())
        # user is redirected if form submitted successfully
        self.assertEqual(response.status_code, 302)

    def test_perform_in_progress_no_data(self):
        """Test list should be allowed to be saved with no data if it is in progress"""
        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
            "in_progress": True,
        }

        response = self.client.post(self.url, data=data)

        self.assertTrue(1, models.TestListInstance.objects.in_progress().count())
        self.assertTrue(len(self.tests), models.TestInstance.objects.in_progress().count())
        # user is redirected if form submitted successfully
        self.assertEqual(response.status_code, 302)

    def set_form_data(self, data):
        for test_idx, uti in enumerate(self.unit_test_infos):
            if uti.test.type == models.UPLOAD:
                data["form-%d-string_value" % test_idx] = self.filename
            if uti.test.type in (models.STRING,):
                data["form-%d-string_value" % test_idx] = "test"
            else:
                data["form-%d-value" % test_idx] = 1
            data["form-%d-comment" % test_idx] = ""

    def test_perform_valid(self):
        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        self.set_form_data(data)

        response = self.client.post(self.url, data=data)

        self.assertTrue(1, models.TestListInstance.objects.count())
        self.assertTrue(len(self.tests), models.TestInstance.objects.count())

        # user is redirected if form submitted successfully
        self.assertEqual(response.status_code, 302)

    def test_perform_unscheduled(self):
        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        utils.create_test_list_instance(
            unit_test_collection=self.unit_test_list,
            work_completed=timezone.now() - timezone.timedelta(days=10)
        )

        self.unit_test_list.refresh_from_db()
        expected_due_date = self.unit_test_list.due_date

        data['work_started'] = (timezone.now() - timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        data['include_for_scheduling'] = False
        self.set_form_data(data)

        response = self.client.post(self.url, data=data)
        assert response.status_code == 302

        # not scheduled so due date should remain same
        self.unit_test_list.refresh_from_db()
        assert self.unit_test_list.due_date.date() == expected_due_date.date()

    def test_perform_unscheduled_first_instance(self):

        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        data['work_started'] = (timezone.now() - timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        data['include_for_scheduling'] = False
        self.set_form_data(data)

        assert self.unit_test_list.due_date is None
        response = self.client.post(self.url, data=data)
        assert response.status_code == 302

        # not scheduled so due date should be null still
        self.unit_test_list.refresh_from_db()
        assert self.unit_test_list.due_date is None

    def test_perform_composite_json_warning(self):
        """ensure returing JSON from composites no longer works"""
        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        self.set_form_data(data)
        data['form-2-value'] = json.dumps({'foo': 'bar'})

        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 200)

    def test_flag_with_bool(self):
        self.t_bool.flag_when = True
        self.t_bool.save()
        data = {
            "work_started": "2012-07-11 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        self.set_form_data(data)

        self.client.post(self.url, data=data)
        tli = models.TestListInstance.objects.latest("pk")
        assert tli.flagged

    def test_work_started_work_completed_same(self):
        data = {
            "work_started": "2012-07-11 00:09",
            "work_completed": "2012-07-11 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        self.set_form_data(data)

        self.client.post(self.url, data=data)

        tli = models.TestListInstance.objects.first()
        ws, wc = tli.work_started, tli.work_completed
        assert (wc - ws).total_seconds() == 60

    def test_perform_valid_invalid_status(self):
        data = {
            "work_started": "2012-11-07 00:09",
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        self.set_form_data(data)

        self.client.post(self.url, data=data)
        self.assertTrue(1, models.TestListInstance.objects.count())

    def test_perform_invalid_work_started(self):
        data = {
            "work_completed": "2050-11-07 00:10",
            "work_started": "2050-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        self.set_form_data(data)

        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 200)

    def test_perform_valid_redirect(self):
        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        self.set_form_data(data)

        response = self.client.post(self.url + "?next=%s" % reverse("home"), data=data)

        # user is redirected if form submitted successfully
        self.assertEqual(response.status_code, 302)
        self.assertEqual("/", response['location'])

    def test_perform_valid_redirect_non_statff(self):
        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        self.set_form_data(data)

        u2 = utils.create_user(is_staff=False, is_superuser=False, uname="u2")
        u2.groups.add(Group.objects.latest("pk"))
        u2.save()
        self.client.logout()
        self.client.login(username="u2", password="password")

        response = self.client.post(self.url, data=data)

        # user is redirected if form submitted successfully
        self.assertEqual(response.status_code, 302)
        self.assertIn("qc/unit/%d" % self.unit_test_list.unit.number, response._headers['location'][1])

    def test_perform_invalid(self):
        data = {
            "work_completed": "2012-11-07 00:10",
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }

        for test_idx, test in enumerate(self.tests):
            data["form-%d-test" % test_idx] = test.pk
            data["form-%d-comment" % test_idx] = ""

        response = self.client.post(self.url, data=data)

        # no values sent so there should be form errors and a 200 status
        self.assertEqual(response.status_code, 200)

        for f in response.context["formset"].forms:
            if f.unit_test_info.test.skip_required():
                self.assertTrue(len(f.errors) > 0)

    def test_skipped(self):
        data = {
            "work_started": "2012-11-07 00:00",
            "work_completed": "2012-11-07 00:10",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": "0",
            "form-MAX_NUM_FORMS": "",
        }

        for test_idx, test in enumerate(self.tests):
            data["form-%d-test" % test_idx] = test.pk
            data["form-%d-skipped" % test_idx] = "true"
            data["form-%d-comment" % test_idx] = ""

        response = self.client.post(self.url, data=data)

        # skipped but no comment so there should be form errors and a 200 status
        self.assertEqual(response.status_code, 200)

        for f in response.context["formset"].forms:
            if f.unit_test_info.test.skip_required():
                self.assertTrue(len(f.errors) > 0)

    def test_skipped_no_comment_ok(self):
        data = {
            "work_started": "2012-11-07 00:00",
            "work_completed": "2012-11-07 00:10",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": "0",
            "form-MAX_NUM_FORMS": "",
        }

        for test_idx, test in enumerate(self.tests):
            test.skip_without_comment = True
            test.save()

            data["form-%d-test" % test_idx] = test.pk
            data["form-%d-skipped" % test_idx] = "true"
            data["form-%d-comment" % test_idx] = ""

        response = self.client.post(self.url, data=data)

        # skipped, no comment, but comment not required so should be 302
        self.assertEqual(response.status_code, 302)

    def test_skipped_with_val(self):
        data = {
            "work_started": "2012-11-07 00:09",
            "work_completed": "2012-11-07 00:10",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": "0",
            "form-MAX_NUM_FORMS": "",
        }

        for test_idx, test in enumerate(self.tests):
            data["form-%d-value" % test_idx] = 1
            data["form-%d-test" % test_idx] = test.pk
            data["form-%d-skipped" % test_idx] = "true"
            data["form-%d-comment" % test_idx] = ""

        response = self.client.post(self.url, data=data)

        # skipped but value entered so there should be form errors and a 200 status
        self.assertEqual(response.status_code, 200)

        for f in response.context["formset"].forms:
            if f.unit_test_info.test.skip_required():
                self.assertTrue(len(f.errors) > 0)

    def test_skipped_with_invalid_val(self):
        data = {
            "work_started": "2012-11-07 00:09",
            "work_completed": "2012-11-07 00:10",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": "0",
            "form-MAX_NUM_FORMS": "",
        }

        for test_idx, test in enumerate(self.tests):
            data["form-%d-value" % test_idx] = ""
            data["form-%d-test" % test_idx] = test.pk
            data["form-%d-skipped" % test_idx] = "true"
            data["form-%d-comment" % test_idx] = ""

        response = self.client.post(self.url, data=data)

        # skipped but value entered so there should be form errors and a 200 status
        self.assertEqual(response.status_code, 200)

        for f in response.context["formset"].forms:
            if f.unit_test_info.test.skip_required():
                self.assertTrue(len(f.errors) > 0)

    def test_skipped_not_required(self):

        not_required = [self.t_const, self.t_comp, self.t_string_comp]

        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": "0",
            "form-MAX_NUM_FORMS": "",
        }

        for test_idx, test in enumerate(self.tests):
            data["form-%d-skipped" % test_idx] = "false"
            data["form-%d-test" % test_idx] = test.pk
            data["form-%d-comment" % test_idx] = ""
            if test.type == models.CONSTANT or test not in not_required:
                data["form-%d-value" % test_idx] = 1
            else:
                data["form-%d-value" % test_idx] = ""

        response = self.client.post(self.url, data=data)

        # not skipped but composite, or constant so there should be no form errors and a 302 status
        self.assertEqual(response.status_code, 302)

    def test_comment_required_missing(self):

        self.t_simple.require_comment = True
        self.t_simple.save()

        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }
        self.set_form_data(data)
        response = self.client.post(self.url, data=data)

        # missing comment so should be form error and a 200 status
        self.assertEqual(response.status_code, 200)
        assert 'requires a comment' in response.context['formset'].errors[0]['comment'][0]

    def test_comment_required_ok(self):

        self.t_simple.require_comment = True
        self.t_simple.save()

        data = {
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "form-TOTAL_FORMS": len(self.tests),
            "form-INITIAL_FORMS": len(self.tests),
            "form-MAX_NUM_FORMS": "",
        }
        self.set_form_data(data)
        data["form-0-comment"] = "comment"
        response = self.client.post(self.url, data=data)

        # has comment so should be no form errors and a 302 status
        self.assertEqual(response.status_code, 302)

    def test_cycle(self):
        tl1 = utils.create_test_list(name="tl1")
        tl2 = utils.create_test_list(name="tl2")
        cycle = utils.create_cycle(test_lists=[tl1, tl2])
        utc = utils.create_unit_test_collection(
            test_collection=cycle,
            unit=self.unit_test_list.unit,
            frequency=self.unit_test_list.frequency,
        )
        url = reverse("perform_qa", kwargs={"pk": utc.pk})

        response = self.client.get(url)

        self.assertListEqual(response.context["days"], [(1, "Day 1"), (2, "Day 2")])
        self.assertEqual(response.context["current_day"], 1)
        self.assertEqual(response.context["last_day"], None)

        work_completed = timezone.now()
        utils.create_test_list_instance(unit_test_collection=utc, test_list=tl1, day=0, work_completed=work_completed)
        response = self.client.get(url)
        self.assertEqual(response.context["current_day"], 2)
        self.assertEqual(response.context["last_day"], 1)

        work_completed += timezone.timedelta(days=1)
        utils.create_test_list_instance(unit_test_collection=utc, test_list=tl2, day=1, work_completed=work_completed)

        response = self.client.get(url)
        self.assertEqual(response.context["current_day"], 1)
        self.assertEqual(response.context["last_day"], 2)

    def test_no_status(self):
        models.ReviewStatus.objects.all().delete()
        response = self.client.get(self.url)
        self.assertTrue(len(list(response.context['messages'])) == 1)

    def test_missing_unit_test_info(self):
        self.unit_test_infos[0].delete()
        response = self.client.get(self.url)
        self.assertIn("do not treat", str(list(response.context['messages'])[0]).lower())

    def test_invalid_day(self):

        tl1 = utils.create_test_list(name="tl1")
        tl2 = utils.create_test_list(name="tl2")
        cycle = utils.create_cycle(test_lists=[tl1, tl2])
        utc = utils.create_unit_test_collection(
            test_collection=cycle,
            unit=self.unit_test_list.unit,
            frequency=self.unit_test_list.frequency,
        )

        url = reverse("perform_qa", kwargs={"pk": utc.pk}) + "?day=22"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestAJAXUpload(TestCase):

    def setUp(self):
        self.view = qatrack.qa.views.perform.Upload
        self.url = reverse("upload")
        self.test = utils.create_test('test upload')
        self.test.type = models.UPLOAD
        self.test.calculation_procedure = """

import json
result = json.load(FILE)
"""
        self.test.save()

        self.test_list = utils.create_test_list()
        utils.create_test_list_membership(self.test_list, self.test)

        content = json.dumps({
            "foo": 1.2,
            "bar": [1, 2, 3, 4],
            "baz": {
                "baz1": "test"
            }
        }).encode()
        self.test_file = SimpleUploadedFile("TESTRUNNER_test_file.json", content)

        self.unit_test_info = utils.create_unit_test_info(test=self.test)
        self.client.login(username="user", password="password")

    def tearDown(self):

        import glob
        for f in glob.glob(os.path.join(settings.TMP_UPLOAD_ROOT, "TESTRUNNER*")):
            try:
                os.remove(f)
            except PermissionError as e:
                print(">>> Could not delete %s because %s" % (f, e))

        for a in Attachment.objects.all():
            if os.path.isfile(a.attachment.path):
                try:
                    os.remove(a.attachment.path)
                except PermissionError as e:
                    print(">>> Could not delete %s because %s" % (a, e))

    def test_upload_fname_exists(self):
        response = self.client.post(
            self.url, {
                "test_id": self.test.pk,
                "upload": self.test_file,
                "unit_id": self.unit_test_info.unit.id,
                "test_list_id": self.test_list.id,
                "meta": "{}",
            }
        )
        data = json.loads(response.content.decode("UTF-8"))
        self.assertTrue(os.path.exists(os.path.join(settings.TMP_UPLOAD_ROOT)), data['attachment']["name"])

    def test_invalid_test_id(self):
        response = self.client.post(self.url, {
            "test_id": 200,
            "upload": self.test_file,
            "unit_id": self.unit_test_info.unit.id,
            "test_list_id": self.test_list.id,
            "meta": "{}"
        })
        data = json.loads(response.content.decode("UTF-8"))
        self.assertEqual(data["errors"][0], "Test with that ID does not exist")

    def test_invalid_test(self):
        self.test.calculation_procedure = "result = 1/0"
        self.test.save()
        response = self.client.post(
            self.url, {
                "test_id": self.test.pk,
                "upload": self.test_file,
                "meta": "{}",
                "unit_id": self.unit_test_info.unit.id,
                "test_list_id": self.test_list.id,
            }
        )
        data = json.loads(response.content.decode("UTF-8"))
        self.assertIn("Invalid Test", data["errors"][0])

    def test_upload_results(self):
        response = self.client.post(self.url, {
            "test_id": self.test.pk,
            "upload": self.test_file,
            "meta": "{}",
            "unit_id": self.unit_test_info.unit.id,
            "test_list_id": self.test_list.id,
        })
        data = json.loads(response.content.decode("UTF-8"))
        self.assertEqual(data["result"]["baz"]["baz1"], "test")


class TestBaseEditTestListInstance(TestCase):

    def setUp(self):
        self.view = views.perform.BaseEditTestListInstance()

    def test_form_valid_not_implemented(self):
        self.assertRaises(NotImplementedError, self.view.form_valid, None)


class TestEditTestListInstance(TestCase):

    def setUp(self):

        self.view = views.perform.EditTestListInstance.as_view()
        self.factory = RequestFactory()

        self.status = utils.create_status()

        self.test_list = utils.create_test_list()
        self.test = utils.create_test(name="test_simple")
        self.test_bool = utils.create_test(name="test_bool", test_type=models.BOOLEAN)
        utils.create_test_list_membership(self.test_list, self.test)
        utils.create_test_list_membership(self.test_list, self.test_bool)

        self.utc = utils.create_unit_test_collection(test_collection=self.test_list)
        self.tli = utils.create_test_list_instance(unit_test_collection=self.utc, status=self.status)

        uti = models.UnitTestInfo.objects.get(test=self.test)

        self.ti = utils.create_test_instance(self.tli, unit_test_info=uti, value=1)

        utib = models.UnitTestInfo.objects.get(test=self.test_bool)
        self.tib = utils.create_test_instance(self.tli, unit_test_info=utib, value=1)

        self.url = reverse("edit_tli", kwargs={"pk": self.tli.pk})
        self.client.login(username="user", password="password")
        self.user = User.objects.get(username="user")
        self.user.save()

        self.base_data = {
            "work_completed": "2012-11-07 00:10",
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "testinstance_set-TOTAL_FORMS": "2",
            "testinstance_set-INITIAL_FORMS": "2",
            "testinstance_set-MAX_NUM_FORMS": "",
            "testinstance_set-0-id": self.ti.pk,
            "testinstance_set-0-value": 1,
            "testinstance_set-1-id": self.tib.pk,
            "testinstance_set-1-value": 1,
        }

    def test_get(self):

        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

    def test_edit(self):

        self.base_data.update({
            "testinstance_set-0-value": 88,
        })

        response = self.client.post(self.url, data=self.base_data)

        self.assertEqual(302, response.status_code)
        self.assertEqual(88, models.TestInstance.objects.get(pk=self.ti.pk).value)

    def test_edit_and_flag(self):

        assert not self.tli.flagged
        self.test_bool.flag_when = True
        self.test_bool.save()

        self.client.post(self.url, data=self.base_data)
        self.tli.refresh_from_db()
        assert self.tli.flagged

    def test_blank_status_edit(self):

        self.base_data.update({
            "testinstance_set-0-value": 88,
            "status": "",
        })

        response = self.client.post(self.url, data=self.base_data)

        self.assertEqual(302, response.status_code)
        self.assertEqual(88, models.TestInstance.objects.get(pk=self.ti.pk).value)

    def test_no_review_status_edit(self):

        self.status.requires_review = False
        self.status.save()
        self.base_data.update({"status": self.status.pk})

        self.client.post(self.url, data=self.base_data)

        self.assertEqual(True, models.TestListInstance.objects.get(pk=self.tli.pk).is_reviewed)

    def test_blank_work_completed(self):
        self.tli.work_completed = None
        self.tli.save()
        self.base_data.pop("work_completed")

        response = self.client.post(self.url, data=self.base_data)

        self.assertEqual(302, response.status_code)

    def test_in_progress(self):

        self.base_data.update({"in_progress": True})

        self.client.post(self.url, data=self.base_data)
        ntests = models.Test.objects.count()
        self.assertEqual(models.TestInstance.objects.in_progress().count(), ntests)
        del self.base_data["in_progress"]
        self.client.post(self.url, data=self.base_data)
        self.assertEqual(models.TestInstance.objects.in_progress().count(), 0)

    def test_in_progress_no_data(self):

        data = {
            "work_completed": "2012-11-07 00:10",
            "work_started": "2012-11-07 00:09",
            "status": self.status.pk,
            "testinstance_set-TOTAL_FORMS": "2",
            "testinstance_set-INITIAL_FORMS": "2",
            "testinstance_set-MAX_NUM_FORMS": "",
            "testinstance_set-0-id": self.ti.pk,
            "testinstance_set-1-id": self.tib.pk,
            "in_progress": True,
        }
        self.client.post(self.url, data=data)
        ntests = models.Test.objects.count()
        self.assertEqual(models.TestInstance.objects.in_progress().count(), ntests)

    def test_no_work_completed(self):

        self.base_data.update({"testinstance_set-0-value": 88, "work_completed": ""})

        response = self.client.post(self.url, data=self.base_data)

        self.assertEqual(302, response.status_code)

    def test_no_value(self):

        self.base_data.update({
            "testinstance_set-0-value": "",
        })

        response = self.client.post(self.url, data=self.base_data)

        self.assertEqual(200, response.status_code)

    def test_no_work_started(self):

        del self.base_data["work_started"]

        response = self.client.post(self.url, data=self.base_data)
        self.assertEqual(200, response.status_code)

    def test_start_after_complete(self):

        self.base_data["work_completed"] = "2012-10-07 00:10",

        response = self.client.post(self.url, data=self.base_data)
        self.assertEqual(200, response.status_code)

    def test_start_future(self):
        del self.base_data["work_completed"]
        self.base_data["work_started"] = "2050-10-07 00:10",

        response = self.client.post(self.url, data=self.base_data)
        self.assertEqual(200, response.status_code)

    def test_next_redirect(self):
        """"""
        response = self.client.post(self.url + "?next=%s" % reverse("home"), data=self.base_data)
        self.assertEqual(302, response.status_code)

    def test_invalid_ref_on_edit(self):

        ref = utils.create_reference()
        tol = utils.create_tolerance()
        tol.type = models.PERCENT
        tol.save()

        self.ti.reference = ref
        self.ti.tolerance = tol
        self.ti.save()

        ref.value = 0
        ref.save()

        self.base_data.update({
            "testinstance_set-0-reference": ref.pk,
            "testinstance_set-0-tolerance": tol.pk,
        })

        response = self.client.post(self.url, data=self.base_data)
        ti = models.TestInstance.objects.get(pk=self.ti.pk)

        # if saved with inavlid ref, test list instance should be saved
        # and test instance should be saved with value of None and comment
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(ti.value)
        self.assertNotIn(ti.comment, ("", None))


class TestReviewTestListInstance(TestCase):

    def setUp(self):

        self.view = views.review.ReviewTestListInstance.as_view()
        self.factory = RequestFactory()

        self.status = utils.create_status()
        self.review_status = utils.create_status(name="reviewed", slug="reviewed", is_default=False)
        self.review_status.requires_review = False
        self.review_status.save()

        self.test_list = utils.create_test_list()
        self.test = utils.create_test(name="test_simple")
        utils.create_test_list_membership(self.test_list, self.test)

        self.utc = utils.create_unit_test_collection(test_collection=self.test_list)
        self.tli = utils.create_test_list_instance(unit_test_collection=self.utc)

        uti = models.UnitTestInfo.objects.get(unit=self.utc.unit, test=self.test)

        self.ti = utils.create_test_instance(self.tli, unit_test_info=uti, value=1)

        self.url = reverse("review_test_list_instance", kwargs={"pk": self.tli.pk})
        self.client.login(username="user", password="password")
        self.user = User.objects.get(username="user")
        self.user.save()

        self.base_data = {
            "testinstance_set-TOTAL_FORMS": "1",
            "testinstance_set-INITIAL_FORMS": "1",
            "testinstance_set-MAX_NUM_FORMS": "",
            "testinstance_set-0-id": self.ti.pk,
            "testinstance_set-0-value": 1,
        }

    def test_update(self):

        response = self.client.get(self.url)

        self.base_data.update({
            "status": self.review_status.pk,
        })

        self.assertEqual(1, models.TestListInstance.objects.unreviewed().count())
        response = self.client.post(self.url, data=self.base_data)

        self.assertEqual(302, response.status_code)
        self.tli.refresh_from_db()
        self.assertEqual(self.tli.review_status, self.review_status)
        self.assertEqual(0, models.TestListInstance.objects.unreviewed().count())

    def test_update_still_requires_review(self):

        response = self.client.get(self.url)

        self.review_status.requires_review = True
        self.review_status.save()

        self.base_data.update({
            "status": self.review_status.pk,
        })

        self.assertEqual(1, models.TestListInstance.objects.unreviewed().count())
        response = self.client.post(self.url, data=self.base_data)

        self.assertEqual(302, response.status_code)
        tli = models.TestListInstance.objects.get(pk=self.tli.pk)
        self.assertFalse(tli.is_reviewed)

    def test_review_tli_url(self):
        tli = models.TestListInstance.objects.get(pk=self.tli.pk)
        urls = [
            "/qc/session/review/%s/" % (tli.pk),
            "/qc/session/review/%s" % (tli.pk),
            "/qc/session/review/rtsqa-0/%s/" % (tli.pk),
            "/qc/session/review/rtsqa-0/%s" % (tli.pk),
        ]
        for url in urls:
            resp = self.client.get(url, follow=True)
            assert resp.status_code == 200

    def test_review_tli_url_reverse(self):
        urls = [
            ("/qc/session/review/", {}),
            ("/qc/session/review/1/", {'pk': 1}),
            ("/qc/session/review/rtsqa-0/1/", {'pk': 1, 'rtsqa_form': 'rtsqa-0'}),
        ]
        for url, kwargs in urls:
            assert reverse("review_test_list_instance", kwargs=kwargs) == url


@freeze_time("2018-01-26 23:00")
class TestDueDateOverView(TestCase):

    def setUp(self):

        self.view = views.review.DueDateOverview.as_view()
        self.factory = RequestFactory()

        self.status = utils.create_status()
        self.review_status = utils.create_status(name="reviewed", slug="reviewed", is_default=False)
        self.review_status.requires_review = False
        self.review_status.save()

        self.test_list = utils.create_test_list()
        self.test = utils.create_test(name="test_simple")
        utils.create_test_list_membership(self.test_list, self.test)

        intervals = (
            ("Daily", "daily", 1, 1, 1),
            ("Weekly", "weekly", 7, 7, 9),
            ("Monthly", "monthly", 28, 28, 35),
        )
        self.frequencies = {}
        for t, s, nom, due, overdue in intervals:
            f = utils.create_frequency(name=t, slug=s, interval=due, window_end=overdue)
            self.frequencies[s] = f

        self.utc = utils.create_unit_test_collection(test_collection=self.test_list)
        self.tli = utils.create_test_list_instance(unit_test_collection=self.utc)

        self.url = reverse("overview_due_dates")
        self.client.login(username="user", password="password")
        self.user = User.objects.get(username="user")
        self.user.save()

        self.user.groups.add(Group.objects.latest("pk"))
        self.user.save()

        self.utc.assigned_to = Group.objects.latest("pk")
        self.utc.save()

        now = timezone.now()
        self.today = now
        self.friday = self.today + timezone.timedelta(days=(4 - self.today.weekday()) % 7)
        self.next_friday = self.friday + timezone.timedelta(days=7)
        self.month_end = timezone.make_aware(
            timezone.datetime(now.year, now.month, calendar.mdays[now.month]), timezone.get_current_timezone()
        )
        self.next_month_start = self.month_end + timezone.timedelta(days=1)

    def test_overdue(self):

        self.utc.due_date = self.today - timezone.timedelta(days=1)
        self.utc.save()
        response = self.client.get(self.url)
        self.assertListEqual(response.context_data["due"][0][2], [self.utc])

    def test_due_this_week(self):
        self.utc.due_date = self.friday
        self.utc.save()
        response = self.client.get(self.url)
        if self.today == self.friday:
            self.assertListEqual(response.context_data["due"][0][2], [self.utc])
        else:
            self.assertListEqual(response.context_data["due"][1][2], [self.utc])

    def test_due_next_week(self):

        self.utc.due_date = self.friday + timezone.timedelta(days=3)
        self.utc.save()
        response = self.client.get(self.url)
        self.assertListEqual(response.context_data["due"][2][2], [self.utc])

    def test_due_this_month(self):

        self.utc.due_date = self.next_friday + timezone.timedelta(days=3)
        if self.utc.due_date < self.next_month_start:
            # test only makes sense if not near end of month
            self.utc.save()
            response = self.client.get(self.url)
            self.assertListEqual(response.context_data["due"][3][2], [self.utc])

    def test_due_next_month(self):

        self.utc.due_date = self.next_month_start + timezone.timedelta(days=15)
        self.utc.save()

        response = self.client.get(self.url)
        self.assertListEqual(response.context_data["due"][4][2], [self.utc])


class TestReviewStatusContext(TestCase):

    def setUp(self):

        self.user = utils.create_user(is_superuser=True, uname='user', pwd='pwd')
        self.client.login(username='user', password='pwd')
        self.factory = RequestFactory()

        self.u_1 = u_utils.create_unit()
        self.tl_1 = utils.create_test_list()
        self.t_1 = utils.create_test()
        self.t_2 = utils.create_test()
        self.t_3 = utils.create_test()
        utils.create_test_list_membership(test_list=self.tl_1, test=self.t_1)
        utils.create_test_list_membership(test_list=self.tl_1, test=self.t_2)
        utils.create_test_list_membership(test_list=self.tl_1, test=self.t_3)
        self.utc_1 = utils.create_unit_test_collection(test_collection=self.tl_1, unit=self.u_1)
        self.tli_1 = utils.create_test_list_instance(test_list=self.tl_1)
        self.uti_1 = models.UnitTestInfo.objects.get(unit=self.u_1, test=self.t_1)
        self.uti_2 = models.UnitTestInfo.objects.get(unit=self.u_1, test=self.t_2)
        self.uti_3 = models.UnitTestInfo.objects.get(unit=self.u_1, test=self.t_3)
        utils.create_test_instance(test_list_instance=self.tli_1, unit_test_info=self.uti_1)
        utils.create_test_instance(test_list_instance=self.tli_1, unit_test_info=self.uti_2)
        utils.create_test_instance(test_list_instance=self.tli_1, unit_test_info=self.uti_3)

        Comment(
            submit_date=timezone.now(),
            user=self.user,
            content_object=self.tli_1,
            comment='TestList comment',
            site=get_current_site(self.factory.get(reverse('perform_qa')))
        ).save()

        Comment(
            submit_date=timezone.now(),
            user=self.user,
            content_object=self.t_1,
            comment='Test comment',
            site=get_current_site(self.factory.get(reverse('perform_qa')))
        ).save()

    def test_none_tli(self):
        self.assertEqual({}, views.base.generate_review_status_context(None))

    def test_valid(self):
        context = views.base.generate_review_status_context(self.tli_1)
        assert context['comments'] == 1
        assert context['status']['name'] == self.tli_1.review_status.name
        assert context['status']['valid'] == self.tli_1.review_status.valid
        assert context['status']['requires_review'] == self.tli_1.review_status.requires_review


class TestTrees(TestCase):

    def setUp(self):
        ge = umodels.Vendor.objects.create(name="ge")
        ve = umodels.Vendor.objects.create(name="ve")
        cap = umodels.Vendor.objects.create(name="cap")
        rad = umodels.UnitClass.objects.create(name="Rad")
        pet = umodels.UnitClass.objects.create(name="PET/CT")

        vdc = umodels.UnitType.objects.create(vendor=ve, unit_class=rad, name="VDC 405")
        crc = umodels.UnitType.objects.create(vendor=cap, unit_class=rad, name="CRC-15R")
        d690 = umodels.UnitType.objects.create(vendor=ge, unit_class=pet, name="Discovery 690")
        self.site = u_utils.create_site()

        u1 = umodels.Unit.objects.create(type=vdc, number=1, date_acceptance=timezone.now().date(), site=self.site)
        u2 = umodels.Unit.objects.create(type=crc, number=2, date_acceptance=timezone.now().date(), site=self.site)
        u3 = umodels.Unit.objects.create(type=d690, number=3, date_acceptance=timezone.now().date(), site=self.site)

        t = utils.create_test()
        tl = utils.create_test_list()
        utils.create_test_list_membership(tl, t)
        self.utc1 = utils.create_unit_test_collection(unit=u1, test_collection=tl)
        self.utc2 = utils.create_unit_test_collection(unit=u2, test_collection=tl)
        self.utc3 = utils.create_unit_test_collection(unit=u3, test_collection=tl)

    def test_freq_tree(self):

        tree = trees.BootstrapFrequencyTree([self.utc1.assigned_to]).generate()[0]

        site_nodes = tree['nodes']
        assert len(site_nodes) == 1
        site_node = site_nodes[0]
        assert site_node['text'].startswith(self.site.name)

        # two unit classes
        class_nodes = site_node['nodes']
        assert len(class_nodes) == 2
        class1_node = class_nodes[0]
        first_class = umodels.UnitClass.objects.order_by("name").first().name
        assert class1_node['text'] == first_class
        class1_unit_nodes = class1_node['nodes']
        assert len(class1_unit_nodes) == umodels.Unit.objects.filter(type__unit_class__name=first_class).count()

    def test_cat_tree(self):

        tree = trees.BootstrapCategoryTree([self.utc1.assigned_to]).generate()[0]

        site_nodes = tree['nodes']
        assert len(site_nodes) == 1
        site_node = site_nodes[0]
        assert site_node['text'].startswith(self.site.name)

        # two unit classes
        class_nodes = site_node['nodes']
        assert len(class_nodes) == 2
        class1_node = class_nodes[0]
        first_class = umodels.UnitClass.objects.order_by("name").first().name
        assert class1_node['text'] == first_class
        class1_unit_nodes = class1_node['nodes']
        assert len(class1_unit_nodes) == umodels.Unit.objects.filter(type__unit_class__name=first_class).count()

    def test_base_setup_qs(self):

        with self.assertRaises(NotImplementedError):
            trees.BaseTree([])


class TestAutoSave(TestCase):

    def setUp(self):

        self.url = reverse("autosave")
        self.load_url = reverse("autosave_load")
        user = User.objects.create_superuser("user", "a@b.com", "password")
        self.client.force_login(user)
        self.utc = utils.create_unit_test_collection()

    def test_invalid_payload(self):
        resp = self.client.post(self.url, content_type="application/json", data="[{]")
        assert resp.json() == {'ok': False, 'autosave_id': None}

    def test_new_autosave(self):
        data = {
            'autosave_id': None,
            'meta': {
                'work_started': "12 May 1980",
                'work_completed': None,
                'unit_test_collection_id': self.utc.id,
                'test_list_id': self.utc.tests_object.id,
                'cycle_day': 1,
            },
            'tests': {},
            'comments': {},
            'skips': {},
            'tli_comment': "",
        }

        resp = self.client.post(self.url, content_type="application/json", data=json.dumps(data))
        assert resp.json() == {'ok': True, 'autosave_id': models.AutoSave.objects.latest("pk").pk}

    def test_update_autosave(self):

        auto = models.AutoSave.objects.create(
            unit_test_collection=self.utc,
            test_list=self.utc.tests_object,
            created_by=self.utc.tests_object.created_by,
            modified_by=self.utc.tests_object.created_by,
            data={},
        )

        data = {
            'autosave_id': auto.id,
            'meta': {
                'work_started': "12 May 1980 12:00",
                'work_completed': None,
                'unit_test_collection_id': self.utc.id,
                'test_list_id': self.utc.tests_object.id,
                'cycle_day': 1,
            },
            'tests': {
                'foo': 'bar'
            },
            'comments': {},
            'skips': {},
            'tli_comment': "",
        }

        self.client.post(self.url, content_type="application/json", data=json.dumps(data))

        auto.refresh_from_db()
        assert auto.work_started == timezone.get_current_timezone().localize(timezone.datetime(1980, 5, 12, 12, 0))
        assert auto.data == {
            'tests': {
                'foo': 'bar'
            },
            'comments': {},
            'skips': {},
            'tli_comment': "",
        }

    def test_invalid_day(self):
        data = {
            'autosave_id': None,
            'meta': {
                'work_started': "12 May 1980",
                'work_completed': None,
                'unit_test_collection_id': self.utc.id,
                'test_list_id': self.utc.tests_object.id,
                'cycle_day': "a1",
            },
            'tests': {},
            'comments': {},
            'skips': {},
            'tli_comment': "",
        }

        resp = self.client.post(self.url, content_type="application/json", data=json.dumps(data))
        auto = models.AutoSave.objects.latest("pk")
        assert resp.json() == {'ok': True, 'autosave_id': auto.pk}
        assert auto.day == 0

    def test_load(self):
        auto = models.AutoSave.objects.create(
            unit_test_collection=self.utc,
            test_list=self.utc.tests_object,
            created_by=self.utc.tests_object.created_by,
            modified_by=self.utc.tests_object.created_by,
            data={},
        )
        resp = self.client.get(self.load_url + "?autosave_id=%d" % auto.id)

        assert resp.status_code == 200
        assert resp.json() == {
            'meta': {
                'work_started': None,
                'work_completed': None,
            },
            'data': {},
        }

    def test_load_404(self):
        resp = self.client.get(self.load_url + "?autosave_id=123")
        assert resp.status_code == 404
