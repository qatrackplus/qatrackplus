"""Calculation procedures run under numpy's default error handling (issue 929).

``qatrack/qa/views/charts.py`` used to call ``numpy.seterr(all='raise')`` when
it was imported, which happens as soon as the URLconf loads.  numpy's error
state belongs to the thread that set it, so the effect depended on the web
server:

* gunicorn sync workers serve every request on one thread, so every
  calculation procedure ran with numpy errors turned into exceptions;
* the Windows CherryPy service uses a pool of threads, so only the thread that
  served the first request was affected - the same procedure failed roughly
  one time in ten;
* ``runserver`` starts a fresh thread per request, so it never happened there.

A divide by zero anywhere in an array - which pylinac's DRGS and DRMLC analyses
do on every image, outside the field - stopped the procedure with
``FloatingPointError``, and ``warnings.filterwarnings`` could not help because
nothing was being warned.

Procedures now run with numpy's defaults, exactly as they do from the command
line.  What protects the results instead is the check on the value a composite
test produces: NaN and infinity, of any float type, are rejected before they can
be shown or saved.
"""

import json
import os
import random
import re

import numpy
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import get_resolver, reverse
from matplotlib.figure import Figure

import qatrack.qa.views.charts  # noqa: F401 - importing it is what used to change the error state
from qatrack.attachments.models import Attachment
from qatrack.qa import models, views
from qatrack.qa.control_chart import control_chart
from qatrack.qa.views.perform import UploadHandler

from . import utils

NUMPY_DEFAULTS = {'divide': 'warn', 'over': 'warn', 'under': 'ignore', 'invalid': 'warn'}

# The same shape of calculation as pylinac's ``dmlc_image.array / open_image.array``:
# one element of the array divides by zero, and the procedure only uses the others.
ARRAY_DIVIDE_BY_ZERO = (
    'import numpy\nratio = numpy.array([1.0, 1.0]) / numpy.array([test1, 0.0])\nresult = float(ratio[0])\n'
)


def strict_json_loads(content):
    """``json.loads`` that refuses NaN and Infinity, the way a browser's ``JSON.parse`` does."""

    def reject(token):
        raise ValueError('%s is not valid JSON' % token)

    return json.loads(content, parse_constant=reject)


class TestNumpyErrorState(TestCase):
    def test_loading_the_urlconf_leaves_numpy_defaults(self):
        """Loading every view must not change how numpy handles errors.

        pytest runs everything on one thread and imports each module once, so
        this asserts on the state itself rather than relying on which test
        happened to import ``charts`` first.
        """
        get_resolver().url_patterns
        self.assertEqual(numpy.geterr(), NUMPY_DEFAULTS)

    def test_no_module_sets_numpy_error_state_globally(self):
        """``numpy.seterr`` changes the whole thread, so nothing in qatrack/ may call it.

        Code that needs different handling should use ``with numpy.errstate(...)``,
        which puts the old state back when the block ends.  Checked statically as
        well, because an import-time call only shows up after its module loads.
        """
        pattern = re.compile(r'\b(?:np|numpy)\.seterr\s*\(')
        offenders = []
        for dirpath, dirnames, filenames in os.walk(settings.PROJECT_ROOT):
            dirnames[:] = [d for d in dirnames if d not in ('migrations', '__pycache__', 'static')]
            for name in filenames:
                if not name.endswith('.py') or name == os.path.basename(__file__):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding='utf-8') as f:
                    for n, line in enumerate(f, 1):
                        if pattern.search(line.split('#', 1)[0]):
                            offenders.append('%s:%d' % (os.path.relpath(path, settings.BASE_DIR), n))

        self.assertEqual(offenders, [])


class TestCompositeNumpyErrors(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = views.perform.CompositeCalculation.as_view()
        self.url = reverse('composite')

        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.test_list = utils.create_test_list()
        self.t1 = utils.create_test(name='test1')
        self.tc = utils.create_test(name='testc', test_type=models.COMPOSITE)
        for t in [self.t1, self.tc]:
            utils.create_test_list_membership(self.test_list, t)
            utils.create_unit_test_info(test=t, unit=self.unit)

        # as the first request to a worker would
        get_resolver().url_patterns

    def calculate(self, procedure):
        self.tc.calculation_procedure = procedure
        self.tc.save()
        data = {
            'tests': {'testc': '', 'test1': 1},
            'meta': {},
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
        }
        request = self.factory.post(self.url, content_type='application/json', data=json.dumps(data))
        request.user = self.user
        response = self.view(request)
        return strict_json_loads(response.content.decode('UTF-8'))['results']['testc']

    def test_array_divide_by_zero_does_not_stop_the_procedure(self):
        result = self.calculate(ARRAY_DIVIDE_BY_ZERO)
        self.assertIsNone(result['error'])
        self.assertEqual(result['value'], 1.0)

    def test_non_finite_results_are_rejected(self):
        """NaN and both infinities are refused whatever float type they arrive as.

        Before issue 929 only ``numpy.nan`` itself and positive Python infinity
        were caught; everything else reached the browser as invalid JSON, and
        through the API was saved.
        """
        procedures = {
            'float nan': "result = float('nan')",
            'numpy.nan': 'import numpy\nresult = numpy.nan',
            'calculated float64 nan': 'import numpy\nresult = numpy.float64(numpy.nan) * test1',
            'float32 nan': "import numpy\nresult = numpy.float32('nan')",
            'float inf': "result = float('inf')",
            'float -inf': "result = float('-inf')",
            'calculated -inf': 'import numpy\nresult = numpy.log(test1 - 1)',
            'float32 inf': "import numpy\nresult = numpy.float32('inf')",
            'float16 -inf': "import numpy\nresult = numpy.float16('-inf')",
        }
        for name, procedure in procedures.items():
            with self.subTest(name):
                result = self.calculate(procedure)
                self.assertIsNone(result['value'])
                self.assertIn('has a result of', result['error'])

    def test_finite_numbers_of_any_type_are_accepted(self):
        procedures = {
            'float32': 'import numpy\nresult = numpy.float32(1.5)',
            'float64': 'import numpy\nresult = numpy.float64(test1) / 4',
            'int64': 'import numpy\nresult = numpy.int64(3)',
            # too big for a float: checking it for NaN must not raise OverflowError
            'huge int': 'result = 10 ** 400',
        }
        for name, procedure in procedures.items():
            with self.subTest(name):
                result = self.calculate(procedure)
                self.assertIsNone(result['error'])
                self.assertIsNotNone(result['value'])


class TestUploadNumpyErrors(TestCase):
    def setUp(self):
        self.user = utils.create_user()
        self.unit = utils.create_unit()
        self.test_list = utils.create_test_list()
        self.test = utils.create_test(name='testu', test_type=models.UPLOAD)
        self.test.calculation_procedure = ARRAY_DIVIDE_BY_ZERO.replace('test1', '1.0').replace(
            'result = float(ratio[0])', "result = {'ratio': float(ratio[0])}"
        )
        self.test.save()
        utils.create_test_list_membership(self.test_list, self.test)
        utils.create_unit_test_info(test=self.test, unit=self.unit)
        self.client.login(username='user', password='password')

        get_resolver().url_patterns

    def tearDown(self):
        for a in Attachment.objects.all():
            if os.path.isfile(a.attachment.path):
                try:
                    os.remove(a.attachment.path)
                except PermissionError:
                    pass

    def test_upload_view(self):
        response = self.client.post(
            reverse('upload'),
            {
                'test_id': self.test.pk,
                'upload': SimpleUploadedFile('TESTRUNNER_929.txt', b'data'),
                'meta': '{}',
                'unit_id': self.unit.id,
                'test_list_id': self.test_list.id,
            },
        )
        data = strict_json_loads(response.content.decode('UTF-8'))
        self.assertEqual(data['errors'], [])
        self.assertEqual(data['result'], {'ratio': 1.0})

    def test_upload_handler(self):
        """The API runs uploads through ``UploadHandler`` rather than the view."""
        data = {
            'test_list_id': self.test_list.id,
            'unit_id': self.unit.id,
            'test_id': self.test.pk,
            'meta': {},
            'comments': {},
            'skips': {},
        }
        results = UploadHandler(self.user, data, SimpleUploadedFile('TESTRUNNER_929.txt', b'data')).process()
        self.assertEqual(results['errors'], [])
        self.assertEqual(results['result'], {'ratio': 1.0})


class TestControlChartFit(TestCase):
    """The fit lines on a control chart depend on the error handling the fit runs under.

    Under the old global ``raise``, the fit failed for almost any data - even
    data drawn from a normal distribution - and the chart quietly showed no fit.
    The fit now runs with numpy errors ignored, which is what its authors
    intended, and a fit that produces NaN or infinity is still treated as no fit.
    """

    def render(self, data):
        fig = Figure()
        control_chart.display(fig, numpy.array(data), 2, 2, fit=True)
        texts = [t.get_text() for ax in fig.axes for t in ax.texts]
        legends = [t.get_text() for ax in fig.axes if ax.get_legend() for t in ax.get_legend().get_texts()]
        return texts, legends

    def test_normally_distributed_data_gets_a_fit(self):
        rng = random.Random(929)
        texts, legends = self.render([rng.gauss(1, 0.5) for _ in range(40)])
        self.assertTrue(any('fit mean' in t for t in texts))
        self.assertIn(control_chart.LBL_GAUSS, legends)
        self.assertEqual(numpy.geterr(), NUMPY_DEFAULTS)

    def test_gamma_curve_that_cannot_be_drawn_leaves_the_gaussian_fit(self):
        """Tightly clustered data gets the Gaussian fit, without an empty Gamma line.

        For data like 100 +/- 0.5 the Gamma shape parameter is huge, so its curve
        works out to NaN at every point. It used to appear in the legend with
        nothing drawn; now only the Gamma part of the fit is left out.
        """
        rng = random.Random(929)
        fig = Figure()
        control_chart.display(fig, numpy.array([rng.gauss(100, 0.5) for _ in range(40)]), 2, 2, fit=True)
        ax_hist_data = fig.axes[1]

        legend = [t.get_text() for t in ax_hist_data.get_legend().get_texts()]
        self.assertIn(control_chart.LBL_GAUSS, legend)
        self.assertNotIn(control_chart.LBL_GAMMA, legend)

        texts = [t.get_text() for t in ax_hist_data.texts]
        self.assertTrue(any('fit mean' in t for t in texts))
        self.assertFalse(any('fit k' in t for t in texts))

        # no histogram anywhere on the chart shows a Gamma line with nothing to draw
        for ax in fig.axes:
            for line in ax.get_lines():
                if line.get_label() == control_chart.LBL_GAMMA:
                    self.assertTrue(numpy.any(numpy.isfinite(line.get_xdata())))
        self.assertEqual(numpy.geterr(), NUMPY_DEFAULTS)

    def test_data_that_cannot_be_fitted_gets_no_fit(self):
        """Constant data gives a zero-width fit, which used to be dropped and still is."""
        texts, legends = self.render([1.1] * 10)
        self.assertFalse(any('fit mean' in t for t in texts))
        self.assertNotIn(control_chart.LBL_GAUSS, legends)
        self.assertEqual(numpy.geterr(), NUMPY_DEFAULTS)
