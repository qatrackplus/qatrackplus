from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import setup_test_environment
from django.utils import unittest,timezone
from qatrack.qa import models,views,forms
from qatrack import settings

import django.forms
import utils

#============================================================================
class TestTestInstanceForm(TestCase):
    """Incomplete but most form functionality is covered in the test_views"""
    #----------------------------------------------------------------------
    def setUp(self):
        self.test_instance = utils.create_test_instance()
    #----------------------------------------------------------------------
    def test_no_instance(self):
        f = forms.TestInstanceForm(instance=None)
        self.assertIsNone(f.setup_form())

