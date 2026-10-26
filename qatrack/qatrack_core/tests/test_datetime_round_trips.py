"""Every date and time must survive every hop between the server and the browser.

A date goes wrong in QATrack+ when one side writes it in one format and the other side
reads it in another. Nothing raises: the date picker or moment quietly produces a
different date, and that is what gets saved, reported or calculated with. So these
tests do not check formats against each other; they push a known date through each hop
and check the same date comes out:

* browser formats    - the formats the page actually sends (siteConfig), per language
* server -> browser  - pre-filled form fields, autosaves, calculated defaults, unit
                       availability data, saved report ranges
* browser -> server  - what each picker writes, read by its form field, the report
                       filter, the chart view and the calculation context
* calculations       - a calculated test using date and datetime values a picker wrote
* API                - what the JSON encoder writes, read back by the parsers

Each hop is checked in every interface language (plus one the site adds, as
docs/tutorials/internationalization/add_language.rst describes) and under several
QATRACK_*_FORMAT settings, because every date defect found in 4.0.x held for one
language or one format only.
"""
import datetime
import importlib
import json
import sys

from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import reset_format_cache
from django.utils.translation import override

import qatrack.formats
from qatrack.accounts.tests.utils import create_user
from qatrack.faults import forms as fault_forms
from qatrack.faults.tests import utils as fault_utils
from qatrack.qa import models as qa_models
from qatrack.qa import views as qa_views
from qatrack.qa.tests import utils as qa_utils
from qatrack.qa.views import forms as qa_forms
from qatrack.qatrack_core import dateformats
from qatrack.qatrack_core.dates import parse_date, parse_datetime
from qatrack.qatrack_core.serializers import QATrackJSONEncoder
from qatrack.qatrack_core.tests import picker
from qatrack.reports.filters import RelativeDateRangeField
from qatrack.reports.forms import value_to_serializable
from qatrack.service_log import forms as sl_forms
from qatrack.service_log.tests import utils as sl_utils
from qatrack.units import forms as unit_forms
from qatrack.units import models as unit_models

# 3 May: reads as 5 March if day and month are swapped. 00:54: 4.0.0 read the hour and
# minute as month and day and saved 23 January.
WHEN = datetime.datetime(2026, 5, 3, 0, 54)
DAY = datetime.date(2026, 5, 3)
OTHER_DAY = datetime.date(2026, 1, 2)

# Shipped languages, plus one added the way the documentation describes.
LANGUAGES = [
    ("en", "English"), ("fr", "Français"), ("fr-ca", "Français (Canada)"),
    ("es", "Español"), ("de", "Deutsch"),
]

# (QATRACK_DATETIME_FORMAT, QATRACK_DATE_FORMAT); None means the shipped default
FORMATS = [
    (None, None),
    ("%d/%m/%Y %H:%M", "%d/%m/%Y"),        # day first
    ("%m/%d/%Y %I:%M %p", "%m/%d/%Y"),     # month first, 12 hour
    ("%d %b %Y %H:%M", "%d %b %Y"),        # the pre-4.0.2 display
    ("%d.%m.%Y %Hh%M", "%d.%m.%Y"),        # a literal letter ("14h30")
]


def reload_formats():
    """Re-derive every loaded format module from the current settings.

    The formats are computed at import, so a settings override needs a reload; this covers
    every language's module (test_dateformats.reload_formats only reloads en and fr).
    """
    from django.utils import formats as django_formats

    from qatrack.formats import base

    importlib.reload(base)
    for name, module in list(sys.modules.items()):
        if name.startswith("qatrack.formats.") and name.endswith(".formats") and module is not base:
            importlib.reload(module)
    django_formats.reset_format_cache()


def local(dt):
    """An aware datetime as naive local time, for comparing with what a browser reads."""
    return timezone.localtime(dt).replace(tzinfo=None)


@override_settings(TIME_ZONE="America/Toronto", LANGUAGES=LANGUAGES)
class DateTimeRoundTrip(TestCase):

    def setUp(self):
        Group.objects.get_or_create(name="group")
        self.user = create_user(uname="roundtrip")
        self.client.force_login(self.user)
        self.aware = timezone.make_aware(WHEN)

    def tearDown(self):
        reload_formats()
        super().tearDown()

    def configurations(self):
        """Yield (label, siteConfig formats) with the format and language active."""
        for dt_fmt, d_fmt in FORMATS:
            settings = {}
            if dt_fmt:
                settings = {"QATRACK_DATETIME_FORMAT": dt_fmt, "QATRACK_DATE_FORMAT": d_fmt}
            with override_settings(**settings):
                reload_formats()
                if hasattr(qatrack.formats, "register_format_modules"):
                    qatrack.formats.register_format_modules()
                reset_format_cache()
                for lang, _name in LANGUAGES:
                    with override(lang):
                        page = self.client.get("/accounts/login/", headers={"accept-language": lang})
                        yield "%s / %s" % (dt_fmt or "default", lang), picker.site_config(page.content.decode())


class TestBrowserFormats(DateTimeRoundTrip):
    """The formats the page sends are the configured ones, intact, in every language."""

    def test_site_config_carries_the_configured_format(self):
        for (label, config), (dt_fmt, d_fmt) in zip(
            self.configurations(), [f for f in FORMATS for _ in LANGUAGES]
        ):
            dt_fmt = dt_fmt or "%Y-%m-%d %H:%M"
            d_fmt = d_fmt or "%Y-%m-%d"
            expected = {
                "FLATPICKR_DATETIME_FMT": dateformats.to_flatpickr(dt_fmt),
                "FLATPICKR_DATE_FMT": dateformats.to_flatpickr(d_fmt),
                "MOMENT_DATETIME_FMT": dateformats.to_moment(dt_fmt),
                "MOMENT_DATE_FMT": dateformats.to_moment(d_fmt),
                "DATERANGEPICKER_DATE_FMT": dateformats.to_moment(d_fmt),
                "MOMENT_DATE_DATA_FMT": "DD-MM-YYYY",
            }
            assert config == expected, label


class TestServerToBrowser(DateTimeRoundTrip):
    """Every value the server hands to a picker or to moment reads back as the same date."""

    def test_new_qc_session_work_started(self):
        """Perform page: Work Started is pre-filled with now, then read by the duration entry too."""
        for label, config in self.configurations():
            before = local(timezone.now()).replace(second=0, microsecond=0)
            text = qa_forms.CreateTestListInstanceForm().fields["work_started"].initial
            after = local(timezone.now()).replace(second=0, microsecond=0)
            assert picker.read_flatpickr(text, config["FLATPICKR_DATETIME_FMT"]) in (before, after), label
            assert picker.read_moment(text, config["MOMENT_DATETIME_FMT"]) in (before, after), label

    def test_existing_records(self):
        """Edit pages: QC session, fault and service event dates arrive pre-filled."""
        tli = qa_utils.create_test_list_instance(work_completed=self.aware)
        qa_models.TestListInstance.objects.filter(pk=tli.pk).update(work_started=self.aware)
        tli.refresh_from_db()
        fault = fault_utils.create_fault(occurred=self.aware)
        se = sl_utils.create_service_event(datetime_service=self.aware)

        def rendered(form, name):
            bound = form[name]
            return bound.field.widget.format_value(bound.value())

        for label, config in self.configurations():
            fmt = config["FLATPICKR_DATETIME_FMT"]
            tli_form = qa_forms.UpdateTestListInstanceForm(instance=tli)
            for text, what in [
                (rendered(tli_form, "work_started"), "work_started"),
                (rendered(tli_form, "work_completed"), "work_completed"),
                (rendered(fault_forms.FaultForm(instance=fault), "occurred"), "fault occurred"),
                (rendered(sl_forms.ServiceEventForm(instance=se, user=self.user), "datetime_service"), "service date"),
            ]:
                assert picker.read_flatpickr(text, fmt) == WHEN, "%s: %s" % (label, what)

    def test_autosave_reload(self):
        utc = qa_utils.create_unit_test_collection()
        auto = qa_models.AutoSave.objects.create(
            unit_test_collection=utc, test_list=utc.tests_object, day=0,
            work_started=self.aware, work_completed=self.aware + datetime.timedelta(minutes=30),
            created_by=self.user, modified_by=self.user, data={"tests": {}, "comments": {}, "skips": {}},
        )
        for label, config in self.configurations():
            lang = label.split(" / ")[1]
            meta = self.client.get(reverse("autosave_load"), {"autosave_id": auto.pk},
                                   headers={"accept-language": lang}).json()["meta"]
            assert picker.read_flatpickr(meta["work_started"], config["FLATPICKR_DATETIME_FMT"]) == WHEN, label

    def test_defaults_from_a_calculation_procedure(self):
        """docs/admin/qa/tests.rst: `your_date_test = timezone.now().date()`, sent to the picker."""
        unit = qa_utils.create_unit()
        test_list = qa_utils.create_test_list()
        procedures = {
            "d_default": (qa_models.DATE, "import datetime\nd_default = datetime.date(2026, 5, 3)"),
            # 04:54 UTC is 00:54 in Toronto; timezone.now() returns an aware UTC datetime like this
            "dt_default": (qa_models.DATETIME,
                           "import datetime\ndt_default = datetime.datetime(2026, 5, 3, 4, 54, tzinfo=datetime.UTC)"),
        }
        for slug, (type_, procedure) in procedures.items():
            t = qa_utils.create_test(name=slug, test_type=type_)
            t.calculation_procedure = procedure
            t.save()
            qa_utils.create_test_list_membership(test_list, t)
            qa_utils.create_unit_test_info(test=t, unit=unit)

        for label, config in self.configurations():
            results = composite(self.user, test_list, unit, {"d_default": "", "dt_default": ""}, defaults=True)
            d = picker.read_flatpickr(results["d_default"]["value"], config["FLATPICKR_DATE_FMT"])
            dt = picker.read_flatpickr(results["dt_default"]["value"], config["FLATPICKR_DATETIME_FMT"])
            assert d.date() == DAY, label
            assert dt == WHEN, label

    def test_a_procedure_that_sets_a_string_does_not_break(self):
        """@nsmela, q#873: `result = "2026-05-03"` raised AttributeError.

        `value_for_browser` branched on the *test's* type, so a date test was
        always sent through `format_as_date` whatever its procedure produced -
        and `strftime` on a `str` surfaced to the user as "Invalid Test
        Procedure". It worked before this PR, so it was a regression.

        A parseable string is now normalised to the display format, which is
        what the picker needs; the value must come back as the configured
        format rather than as whatever the procedure wrote.
        """
        unit = qa_utils.create_unit()
        test_list = qa_utils.create_test_list()
        procedures = {
            "d_str": (qa_models.DATE, 'd_str = "2026-05-03"'),
            "dt_str": (qa_models.DATETIME, 'dt_str = "2026-05-03 04:54"'),
        }
        for slug, (type_, procedure) in procedures.items():
            test = qa_utils.create_test(name=slug, test_type=type_)
            test.calculation_procedure = procedure
            test.save()
            qa_utils.create_test_list_membership(test_list, test)
            qa_utils.create_unit_test_info(test=test, unit=unit)

        for label, config in self.configurations():
            results = composite(self.user, test_list, unit, {"d_str": "", "dt_str": ""}, defaults=True)
            for slug in procedures:
                assert results[slug]["error"] is None, "%s: %s" % (label, results[slug])
            d = picker.read_flatpickr(results["d_str"]["value"], config["FLATPICKR_DATE_FMT"])
            assert d.date() == DAY, label

    def test_a_procedure_that_sets_an_unreadable_string_is_left_alone(self):
        """Not a date at all, so it keeps the behaviour it had before this PR.

        Deliberately unlike `autosave_load`, which drops what it cannot read:
        there the value is known to be a date in a stale format, so handing it
        to the picker risks a silently wrong date. Here it never was a date, and
        inventing a new behaviour for a broken procedure is not this PR's job.
        """
        unit = qa_utils.create_unit()
        test_list = qa_utils.create_test_list()
        test = qa_utils.create_test(name="d_junk", test_type=qa_models.DATE)
        test.calculation_procedure = 'd_junk = "not a date at all"'
        test.save()
        qa_utils.create_test_list_membership(test_list, test)
        qa_utils.create_unit_test_info(test=test, unit=unit)

        results = composite(self.user, test_list, unit, {"d_junk": ""}, defaults=True)
        assert results["d_junk"]["error"] is None, results["d_junk"]
        assert results["d_junk"]["value"] == "not a date at all"

    def test_unit_available_time_calendar(self):
        unit = qa_utils.create_unit()
        unit.date_acceptance = OTHER_DAY
        unit.save()
        unit_models.UnitAvailableTimeEdit.objects.create(unit=unit, date=DAY, hours=datetime.timedelta(hours=8))
        uat = unit_models.UnitAvailableTime.objects.filter(unit=unit).first()
        for label, config in self.configurations():
            lang = label.split(" / ")[1]
            data = self.client.get(reverse("get_unit_available_time_data"),
                                   headers={"accept-language": lang}).json()["unit_available_time_data"][str(unit.pk)]
            fmt = config["MOMENT_DATE_FMT"]
            assert picker.read_moment(data["date_acceptance"], fmt).date() == OTHER_DAY, label
            assert [picker.read_moment(k, fmt).date() for k in data["available_time_edits"]] == [DAY], label
            if uat:
                changed = picker.read_moment(uat.to_dict()["date_changed"], config["MOMENT_DATE_DATA_FMT"])
                assert changed.date() == uat.date_changed, label


class TestBrowserToServer(DateTimeRoundTrip):
    """What each picker writes is read back by the server as the same date."""

    def test_form_fields(self):
        for label, config in self.configurations():
            dt_text = picker.write_flatpickr(WHEN, config["FLATPICKR_DATETIME_FMT"])
            d_text = picker.write_flatpickr(DAY, config["FLATPICKR_DATE_FMT"])
            tli_fields = qa_forms.BaseTestListInstanceForm().fields
            ti_fields = qa_forms.CreateTestInstanceForm().fields
            for field, what in [
                (tli_fields["work_started"], "work_started"),
                (tli_fields["work_completed"], "work_completed"),
                (fault_forms.FaultForm().fields["occurred"], "fault occurred"),
                (sl_forms.ServiceEventForm(user=self.user).fields["datetime_service"], "service date"),
                (ti_fields["datetime_value"], "datetime test"),
            ]:
                assert local(field.clean(dt_text)) == WHEN, "%s: %s read %r" % (label, what, dt_text)
            for field, what in [
                (ti_fields["date_value"], "date test"),
                (unit_forms.UnitAvailableTimeForm().fields["date_changed"], "unit schedule change"),
                (unit_forms.UnitAvailableTimeEditForm().fields["date"], "unit one-off change"),
            ]:
                assert field.clean(d_text) == DAY, "%s: %s read %r" % (label, what, d_text)

    def test_reports_and_charts(self):
        """Report filter, saved report, and the chart view's date range."""
        for label, config in self.configurations():
            fmt = config["DATERANGEPICKER_DATE_FMT"]
            written = "%s - %s" % (picker.write_moment(OTHER_DAY, fmt), picker.write_moment(DAY, fmt))

            start, end = RelativeDateRangeField().clean(written)
            assert (start.date(), end.date()) == (OTHER_DAY, DAY), "%s: report filter read %r" % (label, written)

            # saved, then shown again in the range picker, then run again
            stored = json.loads(json.dumps([start, end], cls=QATrackJSONEncoder))
            shown = value_to_serializable(stored, "RelativeDateRangeField")
            assert [picker.read_moment(p, fmt).date() for p in shown.split(" - ")] == [OTHER_DAY, DAY], label
            start, end = RelativeDateRangeField().clean(shown)
            assert (start.date(), end.date()) == (OTHER_DAY, DAY), "%s: saved report read %r" % (label, shown)

            # qa/views/charts.py reads the chart range with parse_date
            assert parse_date(picker.write_moment(DAY, fmt)) == DAY, label


class TestCalculations(DateTimeRoundTrip):
    """A calculated test sees the dates the pickers wrote, not some other date."""

    def test_calculation_with_picked_dates(self):
        unit = qa_utils.create_unit()
        test_list = qa_utils.create_test_list()
        for slug, type_ in [("d_in", qa_models.DATE), ("dt_in", qa_models.DATETIME)]:
            t = qa_utils.create_test(name=slug, test_type=type_)
            qa_utils.create_test_list_membership(test_list, t)
            qa_utils.create_unit_test_info(test=t, unit=unit)
        calc = qa_utils.create_test(name="elapsed", test_type=qa_models.COMPOSITE)
        calc.calculation_procedure = "import datetime\nelapsed = (dt_in - datetime.datetime.combine(d_in, datetime.time(), dt_in.tzinfo)).total_seconds()"
        calc.save()
        qa_utils.create_test_list_membership(test_list, calc)
        qa_utils.create_unit_test_info(test=calc, unit=unit)
        expected = (WHEN - datetime.datetime.combine(OTHER_DAY, datetime.time())).total_seconds()

        for label, config in self.configurations():
            values = {
                "d_in": picker.write_flatpickr(OTHER_DAY, config["FLATPICKR_DATE_FMT"]),
                "dt_in": picker.write_flatpickr(WHEN, config["FLATPICKR_DATETIME_FMT"]),
                "elapsed": "",
            }
            result = composite(self.user, test_list, unit, values)["elapsed"]
            assert result["error"] is None, "%s: %s" % (label, result["error"])
            assert result["value"] == expected, "%s: %r" % (label, values)


class TestAPI(TestCase):
    """What the JSON encoder writes, QATrack+'s parsers read back."""

    def tearDown(self):
        reload_formats()
        super().tearDown()

    def check(self):
        written = json.loads(json.dumps({"dt": WHEN, "d": DAY}, cls=QATrackJSONEncoder))
        assert parse_datetime(written["dt"]) == WHEN, written
        assert parse_date(written["d"]) == DAY, written

    def test_default_settings(self):
        reload_formats()
        self.check()

    @override_settings(QATRACK_EXTRA_DATETIME_INPUT_FORMATS=["%d %b %Y %H:%M", "%d/%m/%Y %H:%M"],
                       QATRACK_EXTRA_DATE_INPUT_FORMATS=["%Y/%m/%d", "%d %b %Y"])
    def test_with_the_extra_formats_from_config_rst(self):
        reload_formats()
        self.check()


def composite(user, test_list, unit, tests, defaults=False):
    data = {"tests": tests, "meta": {}, "test_list_id": test_list.id, "unit_id": unit.id, "defaults": defaults}
    request = RequestFactory().post(reverse("composite"), content_type="application/json", data=json.dumps(data))
    request.user = user
    response = qa_views.perform.CompositeCalculation.as_view()(request)
    return json.loads(response.content.decode("utf-8"))["results"]
