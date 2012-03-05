from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.test import TestCase
from django.test.client import Client, RequestFactory
from django.utils import unittest
from qatrack.qa.models import TaskList, TaskListItem, Category
from qatrack.units.models import Unit, UnitType, Modality

import json
import qatrack.qa.views

#============================================================================
class QAValidationTest(TestCase):
    """Test class for testing validation views"""

    #----------------------------------------------------------------------
    def test_invalid_task_list(self):
        c = Client()
        validate_url = reverse("validate", args=["1"])
        response = c.get(validate_url, {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            json.loads(response.content),
            {"status": "Invalid Task List ID"}
        )
    #----------------------------------------------------------------------
    def test_composite_context(self):
        """test that the composite test context is set up correctly"""

        factory = RequestFactory()
        request = factory.get(reverse("validate", args=["1"]),  {
            #name: [id, val, skipped]
            "foo":["1", "1.0", "false"],
            "bar":["2", "-22", "false"],
            "baz":["3", "null", "true"],
            "bad":["4", "give me a value error", "false"]
        })

        composite_context = qatrack.qa.views.get_composite_context(request)
        self.assertDictEqual(composite_context, {"foo": 1.0, "bar": -22.})
