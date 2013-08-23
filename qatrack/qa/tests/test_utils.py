from django.test import TestCase

from qatrack.qa import utils
import json


#============================================================================
class TestUtils(TestCase):

    #----------------------------------------------------------------------
    def test_unique(self):
        items = ["foo", "foo", "bar"]
        self.assertListEqual(items[1:], utils.unique(items))

    #----------------------------------------------------------------------
    def test_almost_equal_none(self):
        self.assertFalse(utils.almost_equal(None, None))

    #----------------------------------------------------------------------
    def test_almost_equal_equal(self):
        self.assertTrue(utils.almost_equal(1, 1))

    #----------------------------------------------------------------------
    def test_almost_equal_small(self):
        self.assertTrue(utils.almost_equal(1, 1 + 1E-10))

    #----------------------------------------------------------------------
    def test_almost_equal_zero(self):
        self.assertTrue(utils.almost_equal(0, 0))

    #----------------------------------------------------------------------
    def test_tokenize(self):
        proc = "result = a + 2"
        self.assertListEqual(proc.split(), utils.tokenize_composite_calc(proc))

    #----------------------------------------------------------------------
    def test_set_encoder_set(self):
        self.assertIsInstance(json.dumps(set([1, 2]), cls=utils.SetEncoder), basestring)

    #---------------------------------------------------------------
    def test_float_format(self):
        numbers = (
            (0.999, 3, "0.999"),
            (0.999, 1, "1"),
            (0.999, 2, "1.0"),
            (0.0, 4, "0.000"),
            (-0.0, 4, "0.000"),
            (1234.567, 1, "1e+3"),
            (1234.567, 2, "1.2e+3"),
            (1234.567, 5, "1234.6"),
        )

        for number, prec, expected in numbers:
            #print utils.to_precision(number, prec), expected,utils.to_precision(number, prec)== expected
            #print expected,utils.to_precision(number, prec)== expected
            self.assertEqual(utils.to_precision(number, prec), expected)

