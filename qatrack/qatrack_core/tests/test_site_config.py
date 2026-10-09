"""Every siteConfig key the JavaScript reads must be one site_base.html sets.

site_base.html renders a `siteConfig` object that the front end reads for
formats and feature flags. A key that is not set there is not an error in
JavaScript - it is `undefined`, and whatever consumes it degrades silently.

That is not hypothetical. `unit_available_time.js` asked for
`siteConfig.MOMEN_DATE_DATA_FMT`, missing the T. `moment().format(undefined)`
falls back to ISO 8601, which was then compared against `date_changed` values
rendered as DD-MM-YYYY, so the comparison never matched, `available_time_changed`
was permanently false, and the "C" marker that
units/unit_available_time_change.html documents as "C denotes Schedule Change"
could never be drawn. The "A" acceptance marker beside it worked the whole
time, which is what made it look deliberate.

There is no JavaScript test runner in this project, so this is checked from
Python. It is a text scan rather than a parse, which is enough: the point is
to catch a name that does not exist, and a name is all it looks at.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

SITE_CONFIG_KEY = re.compile(r"^\s*([A-Za-z_][A-Za-z_0-9]*)\s*:", re.M)
SITE_CONFIG_USE = re.compile(r"siteConfig\.([A-Za-z_][A-Za-z_0-9]*)")


def _project_root():
    return Path(settings.PROJECT_ROOT)


def _site_base():
    return _project_root() / "templates" / "site_base.html"


def declared_keys():
    """The keys of the `var siteConfig = {...}` literal in site_base.html."""
    text = _site_base().read_text(encoding="utf-8")
    start = text.index("siteConfig = {")
    end = text.index("};", start)
    return set(SITE_CONFIG_KEY.findall(text[start:end]))


def app_javascript():
    """This project's own JS, from the app static dirs.

    Deliberately excludes settings.STATIC_ROOT (qatrack/static), which holds
    collectstatic output: it is gitignored, may not exist, and when it does it
    is a stale copy of the files below.
    """
    static_root = Path(settings.STATIC_ROOT).resolve()
    for path in sorted(_project_root().glob("*/static/**/*.js")):
        if static_root in path.resolve().parents or path.resolve() == static_root:
            continue
        if "/js/lib/" in path.as_posix() or ".min.js" in path.name:
            continue
        yield path


class TestSiteConfigKeys(SimpleTestCase):

    def test_every_key_read_by_javascript_is_declared(self):
        declared = declared_keys()
        undeclared = {}
        for path in app_javascript():
            for name in SITE_CONFIG_USE.findall(path.read_text(encoding="utf-8", errors="replace")):
                if name not in declared:
                    undeclared.setdefault(name, set()).add(
                        path.relative_to(_project_root()).as_posix()
                    )
        assert undeclared == {}, "\n".join(
            "siteConfig.%s is never set in site_base.html (read by %s)"
            % (name, ", ".join(sorted(files)))
            for name, files in sorted(undeclared.items())
        )

    def test_the_scan_actually_found_something(self):
        """A vacuous pass would hide exactly the bug this guards."""
        assert len(declared_keys()) > 5, declared_keys()
        used = {
            name
            for path in app_javascript()
            for name in SITE_CONFIG_USE.findall(path.read_text(encoding="utf-8", errors="replace"))
        }
        assert len(used) > 5, used

    def test_the_date_format_keys_are_declared(self):
        """The ones this branch's format work depends on, named explicitly."""
        declared = declared_keys()
        for name in [
            "MOMENT_DATE_DATA_FMT",
            "MOMENT_DATE_FMT",
            "MOMENT_DATETIME_FMT",
            "FLATPICKR_DATE_FMT",
            "FLATPICKR_DATETIME_FMT",
            "DATERANGEPICKER_DATE_FMT",
        ]:
            assert name in declared, "%s missing from site_base.html" % name
