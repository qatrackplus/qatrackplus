import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import TestCase

from qatrack.attachments.models import Attachment
from qatrack.qa.views import forms

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
