"""Every date and time format QATrack+ uses, derived from four settings.

Django resolves formats through the modules under ``FORMAT_MODULE_PATH``
*before* it looks at settings, and only for the format names it knows about -
``get_format('FLATPICKR_DATETIME_FMT')`` never consults settings at all,
because that name is not one of Django's. The practical effect used to be that
none of the formats below could be changed from ``local_settings.py``: a
deployer who set one got no effect and no error.

Reading the settings here fixes that, because this module *is* what the locale
format modules are. ``qatrack/formats/en/formats.py`` and its siblings are
one-line imports of this file, so every language gets the same answer - which
is the intent. A date should not change meaning because someone switched the
interface to French.

Everything is derived from the strptime formats in settings, so the display
format, the picker format, the browser format and the help text cannot
disagree with each other or with what the parser accepts.
"""

from django.conf import settings

from qatrack.qatrack_core import dateformats


def _setting(name, default):
    value = getattr(settings, name, None)
    return default if value is None else value


_DATETIME = _setting('QATRACK_DATETIME_FORMAT', '%Y-%m-%d %H:%M')
_DATE = _setting('QATRACK_DATE_FORMAT', '%Y-%m-%d')
_TIME = _setting('QATRACK_TIME_FORMAT', '%H:%M')


def _inputs(primary, extra_setting):
    """The display format first, then any extras, with duplicates dropped.

    Order matters twice over. Django tries input formats in order, so the
    format QATrack+ itself writes should be tried first. And ``forms``
    renders an existing value using ``input_formats[0]``, so if the display
    format were not first, editing a record would rewrite its date into a
    different format than the one the picker produces.
    """
    formats = [primary] + list(_setting(extra_setting, []))
    seen = set()
    return [f for f in formats if not (f in seen or seen.add(f))]


DATETIME_INPUT_FORMATS = _inputs(_DATETIME, 'QATRACK_EXTRA_DATETIME_INPUT_FORMATS')
DATE_INPUT_FORMATS = _inputs(_DATE, 'QATRACK_EXTRA_DATE_INPUT_FORMATS')
TIME_INPUT_FORMATS = _inputs(_TIME, 'QATRACK_EXTRA_TIME_INPUT_FORMATS')

# Server side rendering.
DATETIME_FORMAT = dateformats.to_django(_DATETIME)
DATE_FORMAT = dateformats.to_django(_DATE)
TIME_FORMAT = dateformats.to_django(_TIME)

# Browser side. These are handed to the templates by
# qatrack.context_processors.site and are what the date pickers write into a
# field - which is why they have to be derived from the same source as the
# input formats above, or a picker produces a value its own form rejects.
FLATPICKR_DATETIME_FMT = dateformats.to_flatpickr(_DATETIME)
FLATPICKR_DATE_FMT = dateformats.to_flatpickr(_DATE)

MOMENT_DATETIME_FMT = dateformats.to_moment(_DATETIME)
MOMENT_DATE_FMT = dateformats.to_moment(_DATE)

DATERANGEPICKER_DATE_FMT = dateformats.to_moment(_DATE)

# Deliberately NOT derived from the display format. This one is a wire format,
# not a preference: it is how the browser parses the date_changed strings that
# UnitAvailableTime.to_dict() emits, and that method hard-codes DD-MM-YYYY.
# Following the display setting here would silently break the unit available
# time calendar for any site that changed it.
MOMENT_DATE_DATA_FMT = "DD-MM-YYYY"

# Shown under date fields in forms.
DATETIME_HELP = "Format %s (24h time)" % dateformats.describe(_DATETIME)
DATE_HELP = "Format %s" % dateformats.describe(_DATE)
