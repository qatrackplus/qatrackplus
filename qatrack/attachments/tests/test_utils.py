import os

from django.conf import settings
from django.test import TestCase
import numpy as np
import matplotlib.pyplot as plt

from qatrack.attachments.utils import to_bytes


class TestToBytes(TestCase):

    def setUp(self):
        self.fn = "foo.png"

    def test_mpl_figure(self):
        p = plt.plot([0, 1], [0, 1])[0]
        assert len(to_bytes(p, self.fn)) > 0

    def test_mpl_canvas(self):
        p = plt.plot([0, 1], [0, 1])[0]
        assert len(to_bytes(p.figure.canvas, self.fn)) > 0

    def test_bytes(self):
        inp = b'1010'
        assert to_bytes(inp) == inp

    def test_nparr(self):
        arr = np.array([1])
        assert to_bytes(arr) == arr.tobytes()

    def test_str(self):
        assert to_bytes("1") == b'1'

    def test_unable_to_convert(self):
        assert to_bytes(object()) == bytes()
