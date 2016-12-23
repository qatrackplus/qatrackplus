import json
import os

from django.conf import settings
from django.test import TestCase
import numpy as np
import matplotlib.pyplot as plt

from qatrack.qa import utils as qautils
from qatrack.qa.utils import to_bytes


class TestUtils(TestCase):

    def test_unique(self):
        items = ["foo", "foo", "bar"]
        self.assertListEqual(items[1:], qautils.unique(items))

    def test_almost_equal_none(self):
        self.assertFalse(qautils.almost_equal(None, None))

    def test_almost_equal_equal(self):
        self.assertTrue(qautils.almost_equal(1, 1))

    def test_almost_equal_small(self):
        self.assertTrue(qautils.almost_equal(1, 1 + 1E-10))

    def test_almost_equal_zero(self):
        self.assertTrue(qautils.almost_equal(0, 0))

    def test_tokenize(self):
        proc = "result = a + 2"
        self.assertListEqual(proc.split(), qautils.tokenize_composite_calc(proc))

    def test_set_encoder_set(self):
        self.assertIsInstance(json.dumps(set([1, 2]), cls=qautils.SetEncoder), str)

    def test_float_format(self):
        numbers = (
            (0.999, 3, "0.999"),
            (-0.999, 3, "-0.999"),
            (0.999, 1, "1"),
            (0.999, 2, "1.0"),
            (0.0, 4, "0"),
            (-0.0, 4, "0"),
            (1234.567, 1, "1e+3"),
            (1234.567, 2, "1.2e+3"),
            (1234.567, 5, "1234.6"),
        )

        for number, prec, expected in numbers:
            self.assertEqual(qautils.to_precision(number, prec), expected)


class TestToBytes(TestCase):

    def setUp(self):

        path = os.path.join(settings.PROJECT_ROOT, "qa", "static", "qa", "img", "tux.png")
        self.tux = open(path, "rb")

    def test_mpl_figure(self):
        p = plt.plot([0, 1], [0, 1])[0]
        assert len(to_bytes(p)) > 0

    def test_mpl_canvas(self):
        p = plt.plot([0, 1], [0, 1])[0]
        assert len(to_bytes(p.figure.canvas)) > 0

    def test_bytes(self):
        inp = b'1010'
        assert to_bytes(inp) == inp

    def test_nparr(self):
        arr = np.array([1])
        assert to_bytes(arr) == arr.tobytes()

    def test_str(self):
        assert to_bytes("1") == b'1'

    def test_unable_to_convert(self):
        assert to_bytes(object) == bytes()



if __name__ == "__main__":
    setup_test_environment()
    unittest.main()
