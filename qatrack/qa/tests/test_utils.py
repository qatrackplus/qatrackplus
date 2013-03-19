from django.test import TestCase

from qatrack.qa import utils

#============================================================================


class TestUtils(TestCase):

    #----------------------------------------------------------------------
    def test_unique(self):
        items = ["foo", "foo", "bar"]
        self.assertListEqual(items[1:], utils.unique(items))
