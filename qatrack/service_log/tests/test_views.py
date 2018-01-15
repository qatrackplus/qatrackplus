from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from qatrack.service_log import models
from qatrack.service_log import forms
from qatrack.service_log import views


import calendar
import django.forms
import json
import os
import glob
import random
from . import utils


class MockUser(object):
    def has_perm(self, *args):
        return True

superuser = MockUser()
