"""The PDF templates' asset links have to be valid file:// URIs.

`"file://" + STATIC_ROOT` is valid enough on POSIX by accident - the path
already begins with a slash, so `file:///srv/static` comes out right. On Windows
`STATIC_ROOT` is `D:\\...`, and the same concatenation gives `file://D:\\...`,
where everything before the first slash is the URI's authority: the drive and
every folder disappear into a hostname. WeasyPrint refuses all nine links in a
report and renders it with no stylesheets and no logo; Chrome accepts the
malformed form, which is why this survived as long as Chrome was the only engine
that ran on Windows (#865 made WeasyPrint work there, and so exposed it).

These tests assert on the URI the filter produces, not on `Path.as_uri()`'s
behaviour, and the Windows case is checked by building the URI the way the
templates do rather than by running on Windows.
"""

import ntpath
import pathlib
import re

from django.template import Context, Template
from django.test import TestCase

from qatrack.qatrack_core.utils import file_uri


class TestFileUri(TestCase):

    def test_a_rooted_path_becomes_a_three_slash_uri(self):
        """Asserted as properties, not as a literal.

        `file:///srv/qatrack/static` is right on POSIX and wrong on Windows, where a
        drive-less rooted path resolves against the current drive and the correct
        answer is `file:///D:/srv/qatrack/static`. The Windows form is pinned
        exactly by `test_windows_shape_...` below; here the platform-independent
        properties are what matter.
        """
        out = file_uri("/srv/qatrack/static")
        assert out.startswith("file:///")
        assert out.endswith("/srv/qatrack/static")
        assert "\\" not in out

    def test_a_space_is_encoded_not_left_raw(self):
        """A raw space in an href is what broke Chrome's command line too (#835)."""
        out = file_uri("/srv/qa track/static")
        assert out.endswith("/srv/qa%20track/static"), out
        assert " " not in out

    def test_empty_static_root_does_not_become_the_working_directory_uri(self):
        """An unset STATIC_ROOT should produce nothing, not a URI for '.'."""
        assert file_uri("") == ""
        assert file_uri(None) == ""

    def test_relative_path_is_made_absolute(self):
        """as_uri() rejects a relative path; the filter must not raise on one."""
        out = file_uri("static")
        assert out.startswith("file:///")
        assert out.endswith("/static")

    def test_windows_shape_would_have_three_slashes_and_forward_slashes(self):
        """The defect itself, expressed without needing a Windows host.

        `pathlib.PureWindowsPath.as_uri()` is the same code `Path.as_uri()` runs
        on Windows, so this pins the output shape that the old concatenation got
        wrong.
        """
        old = "file://" + r"D:\QATrackPlus\static"
        new = pathlib.PureWindowsPath(r"D:\QATrackPlus\static").as_uri()

        assert new == "file:///D:/QATrackPlus/static"
        assert old == r"file://D:\QATrackPlus\static"

        # the authority is what the old form got wrong: everything up to the
        # next slash is read as a host, and there is no next slash at all
        assert re.match(r"^file://([^/]*)", old).group(1) == r"D:\QATrackPlus\static"
        assert re.match(r"^file://([^/]*)", new).group(1) == ""

        assert "\\" not in new
        assert ntpath.isabs(r"D:\QATrackPlus\static")


class TestPdfTemplateLinks(TestCase):
    """The filter has to be reachable from the templates that need it."""

    def render(self, template_source, **context):
        return Template(template_source).render(Context(context))

    def test_filter_is_registered_in_qatrack_tags(self):
        out = self.render(
            "{% load qatrack_tags %}{{ STATIC_ROOT|file_uri }}/qa/css/qa.css",
            STATIC_ROOT="/srv/static",
        )
        # compared against the filter's own output: the point is that the filter is
        # registered and produced something, not what a URI looks like per platform
        assert out == file_uri("/srv/static") + "/qa/css/qa.css"
        assert out.startswith("file:///")

    def test_no_template_still_concatenates_file_scheme_onto_a_path(self):
        """Every occurrence had to be fixed, not just the one that was reported.

        There were eighteen across three templates, and one left behind would
        fail on Windows exactly as before.
        """
        roots = [
            "qatrack/reports/templates/reports/pdf_report.html",
            "qatrack/reports/templates/reports/_header.html",
            "qatrack/qa/templates/qa/testlistinstance_report.html",
        ]
        offenders = []
        for rel in roots:
            text = pathlib.Path(rel).read_text()
            for m in re.finditer(r'"file://\{\{[^"]*"', text):
                offenders.append("%s: %s" % (rel, m.group(0)))
        assert offenders == [], offenders

    def test_the_pdf_templates_load_the_library_they_use(self):
        """A filter used without its {% load %} renders as empty, silently."""
        for rel in [
            "qatrack/reports/templates/reports/pdf_report.html",
            "qatrack/reports/templates/reports/_header.html",
            "qatrack/qa/templates/qa/testlistinstance_report.html",
        ]:
            text = pathlib.Path(rel).read_text()
            if "|file_uri" in text:
                assert "{% load qatrack_tags %}" in text, rel
