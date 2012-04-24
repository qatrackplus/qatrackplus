from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.test import TestCase
from django.test.client import Client, RequestFactory
from django.utils import unittest
from qatrack.qa.models import TaskList, TaskListItem, Category
from qatrack.units.models import Unit, UnitType, Modality

import json
import qatrack.qa.views

