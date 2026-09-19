"""Tests for the date/time format settings.

The bug these are written against: a date picker that writes a value its own
form then rejects. That can only happen if the format the browser uses and the
formats the parser accepts are maintained separately, which is exactly how
they were maintained before. So most of what is checked here is not "does the
converter work" but "do the four dialects still agree with each other".
"""

import datetime

from django.forms.fields import DateField, DateTimeField, TimeField
from django.test import TestCase, override_settings
from django.utils.dateformat import format as dj_format
from django.utils.formats import get_format

from qatrack.qatrack_core import dateformats

ISO = "%Y-%m-%d %H:%M"

# Formats a real site might plausibly choose. Any of these has to work end to
# end, not just the default - that is the whole point of making it a setting.
REALISTIC = [
    ("%Y-%m-%d %H:%M", "2026-03-05 09:07"),       # ISO 8601, the default
    ("%m/%d/%Y %H:%M", "03/05/2026 09:07"),       # United States
    ("%d/%m/%Y %H:%M", "05/03/2026 09:07"),       # most of the rest of the world
    ("%d.%m.%Y %H:%M", "05.03.2026 09:07"),       # German / Nordic
    ("%d %b %Y %H:%M", "05 Mar 2026 09:07"),      # the pre-4.1 QATrack+ format
    ("%b %d %Y %H:%M", "Mar 05 2026 09:07"),      # month name first
    ("%d %B %Y %H:%M", "05 March 2026 09:07"),    # full month name
    ("%Y-%m-%d %I:%M %p", "2026-03-05 09:07 AM"),  # 12 hour
]


class TestFormatConversion(TestCase):
    """The strptime -> other dialect translations."""

    def test_iso_datetime(self):
        assert dateformats.to_django(ISO) == "Y-m-d H:i"
        assert dateformats.to_flatpickr(ISO) == "Y-m-d H:i"
        assert dateformats.to_moment(ISO) == "YYYY-MM-DD HH:mm"
        assert dateformats.describe(ISO) == "YYYY-MM-DD hh:mm"

    def test_day_month_year(self):
        fmt = "%d/%m/%Y %H:%M"
        assert dateformats.to_django(fmt) == "d/m/Y H:i"
        assert dateformats.to_flatpickr(fmt) == "d/m/Y H:i"
        assert dateformats.to_moment(fmt) == "DD/MM/YYYY HH:mm"

    def test_named_month(self):
        """The pre-4.1 QATrack+ format, which sites may still prefer."""
        fmt = "%d %b %Y %H:%M"
        assert dateformats.to_django(fmt) == "d M Y H:i"
        assert dateformats.to_flatpickr(fmt) == "d M Y H:i"
        assert dateformats.to_moment(fmt) == "DD MMM YYYY HH:mm"

    def test_month_day_year(self):
        """United States order."""
        fmt = "%m/%d/%Y %H:%M"
        assert dateformats.to_django(fmt) == "m/d/Y H:i"
        assert dateformats.to_flatpickr(fmt) == "m/d/Y H:i"
        assert dateformats.to_moment(fmt) == "MM/DD/YYYY HH:mm"

    def test_month_name_first(self):
        fmt = "%b %d %Y"
        assert dateformats.to_django(fmt) == "M d Y"
        assert dateformats.to_moment(fmt) == "MMM DD YYYY"

    def test_full_month_name(self):
        fmt = "%d %B %Y"
        assert dateformats.to_django(fmt) == "d F Y"
        assert dateformats.to_moment(fmt) == "DD MMMM YYYY"

    def test_twelve_hour_clock(self):
        fmt = "%I:%M %p"
        assert dateformats.to_django(fmt) == "h:i A"
        assert dateformats.to_flatpickr(fmt) == "h:i K"
        assert dateformats.to_moment(fmt) == "hh:mm A"

    def test_every_realistic_format_renders_the_same_in_python_and_django(self):
        """The property that matters: the server and the browser agree.

        Django is the only one of the three target dialects that can be
        rendered from Python, so this is as close as a unit test gets to
        checking that a converted format still describes the same instant.
        """
        moment = datetime.datetime(2026, 3, 5, 9, 7)
        for fmt, expected in REALISTIC:
            assert moment.strftime(fmt) == expected, fmt
            assert dj_format(moment, dateformats.to_django(fmt)) == expected, fmt

    def test_every_realistic_format_round_trips(self):
        """Rendered, then read back, gives the instant you started with."""
        moment = datetime.datetime(2026, 3, 5, 9, 7)
        for fmt, _ in REALISTIC:
            assert datetime.datetime.strptime(moment.strftime(fmt), fmt) == moment, fmt

    def test_every_realistic_format_converts_without_error(self):
        for fmt, _ in REALISTIC:
            for convert in (dateformats.to_django, dateformats.to_flatpickr, dateformats.to_moment):
                assert convert(fmt), fmt

    def test_date_only(self):
        assert dateformats.to_django("%Y-%m-%d") == "Y-m-d"
        assert dateformats.to_moment("%Y-%m-%d") == "YYYY-MM-DD"

    def test_seconds_differ_between_dialects(self):
        """Django spells seconds 's', flatpickr spells it 'S'.

        The kind of difference that makes hand-maintaining four copies a bad
        idea, and the reason these are derived rather than written out.
        """
        fmt = "%H:%M:%S"
        assert dateformats.to_django(fmt) == "H:i:s"
        assert dateformats.to_flatpickr(fmt) == "H:i:S"

    def test_single_digit_values_are_zero_padded(self):
        """Y-m-d has to mean YYYY-MM-DD, not YYYY-M-D.

        Django's unpadded variants are one character away from the padded ones
        - n, j and G rather than m, d and H - so a slip in the mapping would
        render 2026-3-5, which still looks plausible enough to ship. moment
        and flatpickr have the same trap.
        """
        dt = datetime.datetime(2026, 3, 5, 9, 7)

        assert dt.strftime(ISO) == "2026-03-05 09:07"
        assert dj_format(dt, dateformats.to_django(ISO)) == "2026-03-05 09:07"

        # The picker dialects cannot be rendered from Python, so assert the
        # tokens - m/d/H/i and MM/DD/HH/mm are the zero padded ones.
        assert dateformats.to_flatpickr(ISO) == "Y-m-d H:i"
        assert dateformats.to_moment(ISO) == "YYYY-MM-DD HH:mm"

    def test_padded_output_parses_back(self):
        """What is displayed must be re-readable, padding and all."""
        dt = datetime.datetime(2026, 3, 5, 9, 7)
        rendered = dj_format(dt, dateformats.to_django(ISO))
        assert datetime.datetime.strptime(rendered, ISO) == dt

    def test_literal_letters_are_escaped(self):
        """A literal 'T' must not become a format specifier."""
        fmt = "%Y-%m-%dT%H:%M"
        assert dateformats.to_django(fmt) == "Y-m-d\\TH:i"
        assert dateformats.to_moment(fmt) == "YYYY-MM-DD[T]HH:mm"

    def test_unsupported_directive_is_an_error(self):
        """Better to fail loudly than to emit a format that is wrong."""
        for func in (dateformats.to_django, dateformats.to_flatpickr, dateformats.to_moment):
            with self.assertRaises(dateformats.UnsupportedFormat):
                func("%Q")

    def test_trailing_percent_is_an_error(self):
        with self.assertRaises(dateformats.UnsupportedFormat):
            dateformats.to_django("%Y-%m-%d %")


class TestFormatsAgree(TestCase):
    """The four dialects must describe the same format as each other."""

    def test_what_the_picker_writes_is_accepted_by_the_form(self):
        """The regression test for the whole point of this module.

        flatpickr renders using the format handed to it by the context
        processor. If that format is not one the field will parse, every date
        a user picks is rejected with "Enter a valid date/time" - which is a
        product bug that no unit test posting a hard-coded string would catch.
        """
        moment = datetime.datetime(2026, 3, 25, 14, 30)

        for setting, field_class in [
            ('QATRACK_DATETIME_FORMAT', DateTimeField),
            ('QATRACK_DATE_FORMAT', DateField),
            ('QATRACK_TIME_FORMAT', TimeField),
        ]:
            source = get_format(setting.replace('QATRACK_', '').replace('_FORMAT', '_INPUT_FORMATS'))[0]
            # What the picker will put in the box, rendered the same way the
            # browser will render it.
            as_typed = moment.strftime(source)
            field_class().clean(as_typed)  # raises ValidationError if rejected

    def test_display_and_input_agree(self):
        """The first input format and the display format are the same format."""
        assert dateformats.to_django(get_format('DATETIME_INPUT_FORMATS')[0]) == get_format('DATETIME_FORMAT')
        assert dateformats.to_django(get_format('DATE_INPUT_FORMATS')[0]) == get_format('DATE_FORMAT')

    def test_picker_formats_match_the_display_format(self):
        assert get_format('FLATPICKR_DATETIME_FMT') == dateformats.to_flatpickr(
            get_format('DATETIME_INPUT_FORMATS')[0]
        )
        assert get_format('MOMENT_DATETIME_FMT') == dateformats.to_moment(
            get_format('DATETIME_INPUT_FORMATS')[0]
        )

    def test_every_language_uses_the_same_formats(self):
        """A date must not change meaning when the interface language does."""
        from qatrack.formats.en import formats as en
        from qatrack.formats.fr import formats as fr

        for name in ['DATETIME_FORMAT', 'DATE_FORMAT', 'DATETIME_INPUT_FORMATS',
                     'FLATPICKR_DATETIME_FMT', 'MOMENT_DATETIME_FMT']:
            assert getattr(en, name) == getattr(fr, name), name


class TestMultipleInputFormats(TestCase):
    """Several ways of typing a date, one way of showing it back."""

    def test_every_configured_input_format_actually_parses(self):
        """A format nobody can type is worse than useless - it is misleading."""
        moment = datetime.datetime(2026, 3, 25, 14, 30, 45, 123456)
        for fmt in get_format('DATETIME_INPUT_FORMATS'):
            DateTimeField().clean(moment.strftime(fmt))

    def test_alternative_formats_are_accepted(self):
        """The same instant, typed several different ways."""
        expected = datetime.datetime(2026, 3, 25, 14, 30)
        for typed in ["2026-03-25 14:30", "25 Mar 2026 14:30", "2026-03-25 14:30:00"]:
            cleaned = DateTimeField().clean(typed)
            assert (cleaned.year, cleaned.month, cleaned.day) == (expected.year, expected.month, expected.day)
            assert (cleaned.hour, cleaned.minute) == (expected.hour, expected.minute)

    def test_input_format_does_not_affect_display(self):
        """However it was typed, it is shown back in the default format."""
        from django.utils.formats import date_format

        rendered = set()
        for typed in ["2026-03-25 14:30", "25 Mar 2026 14:30", "2026-03-25 14:30:00"]:
            cleaned = DateTimeField().clean(typed)
            rendered.add(date_format(cleaned, get_format('DATETIME_FORMAT')))

        assert len(rendered) == 1, "same instant rendered %d different ways: %r" % (len(rendered), rendered)
        assert rendered.pop().startswith("2026-03-25")

    def test_the_default_format_is_tried_first(self):
        """Django renders an existing value with input_formats[0].

        If the default were not first, editing a record would silently rewrite
        its date into a different format than the picker produces.
        """
        assert get_format('DATETIME_INPUT_FORMATS')[0] == "%Y-%m-%d %H:%M"


class TestDeployerCanOverride(TestCase):
    """The settings have to actually do something - they used not to.

    Before this, `get_format` consulted the locale format modules and, for the
    picker formats, never looked at settings at all. Setting any of these in
    local_settings.py had no effect and produced no error.
    """

    def _reload(self):
        import importlib

        from django.utils import formats as django_formats

        from qatrack.formats import base
        from qatrack.formats.en import formats as en
        from qatrack.formats.fr import formats as fr
        importlib.reload(base)
        importlib.reload(en)
        importlib.reload(fr)
        django_formats.reset_format_cache()

    def tearDown(self):
        self._reload()
        super().tearDown()

    @override_settings(QATRACK_DATETIME_FORMAT="%d/%m/%Y %H:%M")
    def test_changing_the_default_changes_everything_derived(self):
        self._reload()
        assert get_format('DATETIME_FORMAT') == "d/m/Y H:i"
        assert get_format('FLATPICKR_DATETIME_FMT') == "d/m/Y H:i"
        assert get_format('MOMENT_DATETIME_FMT') == "DD/MM/YYYY HH:mm"
        assert get_format('DATETIME_INPUT_FORMATS')[0] == "%d/%m/%Y %H:%M"
        assert "DD/MM/YYYY" in get_format('DATETIME_HELP')

    @override_settings(QATRACK_DATE_FORMAT="%m/%d/%Y", QATRACK_EXTRA_DATE_INPUT_FORMATS=["%d/%m/%Y"])
    def test_us_order_wins_when_it_is_the_display_format(self):
        """03/05/2026 is genuinely ambiguous, so the tie has to break somewhere.

        A site that displays US order and also accepts European order has no
        way to tell 3rd of May from March 5th. It resolves to the display
        format, because that is first in the input list - which is the only
        answer that makes what you type and what you see agree.
        """
        self._reload()
        assert DateField().clean("03/05/2026") == datetime.date(2026, 3, 5)

    @override_settings(QATRACK_DATE_FORMAT="%d/%m/%Y", QATRACK_EXTRA_DATE_INPUT_FORMATS=["%m/%d/%Y"])
    def test_european_order_wins_when_it_is_the_display_format(self):
        """The same input, the same two formats accepted, the other answer."""
        self._reload()
        assert DateField().clean("03/05/2026") == datetime.date(2026, 5, 3)

    @override_settings(QATRACK_DATE_FORMAT="%b %d %Y")
    def test_a_month_name_format_works_end_to_end(self):
        self._reload()
        assert get_format('DATE_FORMAT') == "M d Y"
        assert get_format('MOMENT_DATE_FMT') == "MMM DD YYYY"
        assert DateField().clean("Mar 05 2026") == datetime.date(2026, 3, 5)

    @override_settings(QATRACK_EXTRA_DATETIME_INPUT_FORMATS=["%d.%m.%Y %H:%M"])
    def test_extra_input_formats_are_additive_and_do_not_change_display(self):
        self._reload()
        formats = get_format('DATETIME_INPUT_FORMATS')
        assert "%d.%m.%Y %H:%M" in formats
        assert formats[0] == "%Y-%m-%d %H:%M", "the default must stay first"
        assert get_format('DATETIME_FORMAT') == "Y-m-d H:i", "display must be unchanged"
        DateTimeField().clean("25.03.2026 14:30")
