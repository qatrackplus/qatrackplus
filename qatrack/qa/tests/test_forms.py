import calendar
import glob
import json
import os
import random
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.sites.shortcuts import get_current_site
from django.core.files.base import ContentFile
import django.forms
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from django_comments.models import Comment
from freezegun import freeze_time

from qatrack.attachments.models import Attachment
from qatrack.qa import models, views
from qatrack.qa.views import forms
import qatrack.qa.views.backup
import qatrack.qa.views.base
import qatrack.qa.views.charts
import qatrack.qa.views.perform
import qatrack.qa.views.review
from qatrack.qatrack_core.utils import format_as_date
from qatrack.units import models as u_models

from . import utils


class TestUpdateTestInstanceForm(TestCase):


    def test_format_set(self):
        ti = utils.create_test_instance()
        ti.unit_test_info.test.formatting = "%.5f"
        ti.unit_test_info.test.type = "composite"
        ti.unit_test_info.test.save()

        f = forms.UpdateTestInstanceForm(instance=ti)
        assert f.fields['value'].widget.attrs['data-formatted'] == "1.00000"

    def test_attachments_to_process(self):
        ti = utils.create_test_instance()
        u = utils.create_user()
        filename = "TESTRUNNER.tmp"
        filepath = os.path.join(settings.TMP_UPLOAD_ROOT, filename)

        f = ContentFile("", filepath)

        a = Attachment.objects.create(testinstance=ti, created_by=u, attachment=f)
        f = forms.UpdateTestInstanceForm(instance=ti)
        f.cleaned_data = {'user_attached': "%d" % a.pk}
        assert f.attachments_to_process == [(ti.unit_test_info.pk, a)]
