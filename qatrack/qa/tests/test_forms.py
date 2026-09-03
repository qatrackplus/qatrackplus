import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils.translation import override

from qatrack.attachments.models import Attachment
from qatrack.formats.utils import get_js_format
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


class TestLocalizedDateFormats(TestCase):

    FLATPICKR_EXAMPLES = {
        "d M Y": "12 Aug 2026",
        "d M Y H:i": "12 Aug 2026 14:30",
        "Y-m-d": "2026-08-12",
        "Y-m-d H:i": "2026-08-12 14:30",
        "d/m/Y": "12/08/2026",
        "d/m/Y H:i": "12/08/2026 14:30",
    }

    def test_js_formats_are_resolved_for_all_languages(self):
        keys = [
            "MOMENT_DATE_DATA_FMT",
            "MOMENT_DATE_FMT",
            "MOMENT_DATETIME_FMT",
            "FLATPICKR_DATE_FMT",
            "FLATPICKR_DATETIME_FMT",
            "DATERANGEPICKER_DATE_FMT",
        ]
        for lang, _ in settings.LANGUAGES:
            with override(lang):
                for key in keys:
                    assert get_js_format(key) != key

    def test_flatpickr_and_form_fields_roundtrip_for_all_languages(self):
        for lang, _ in settings.LANGUAGES:
            with override(lang):
                date_str = self.FLATPICKR_EXAMPLES[get_js_format("FLATPICKR_DATE_FMT")]
                datetime_str = self.FLATPICKR_EXAMPLES[get_js_format("FLATPICKR_DATETIME_FMT")]
                form = forms.CreateTestInstanceForm()
                assert form.fields["date_value"].clean(date_str)
                assert form.fields["datetime_value"].clean(datetime_str)

    def test_js_format_falls_back_to_english_for_missing_locale_formats(self):
        with override("de"):
            assert get_js_format("FLATPICKR_DATETIME_FMT") == "d M Y H:i"

    def test_work_started_widget_uses_primary_datetime_input_format(self):
        form = forms.BaseTestListInstanceForm()
        assert form.fields["work_started"].widget.format == settings.DATETIME_INPUT_FORMATS[0]
