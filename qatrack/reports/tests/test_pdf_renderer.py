"""Which engine renders a report PDF, and why.

`settings.PDF_RENDERER` exists because WeasyPrint's layout libraries (pango,
cairo, gdk-pixbuf) are part of an ordinary Linux install and of the Docker
image, but on Windows they arrive only with MSYS2 - a second software stack
an administrator has to choose to install and maintain. So the default,
"auto", means WeasyPrint everywhere except Windows.

These tests pin the resolution rules and the dispatch, because the platform
half of the decision cannot be exercised by the CI job that runs them.
"""

from unittest import mock

from django.core.checks import Error, Warning
from django.test import TestCase
from django.test.utils import override_settings

from qatrack.qatrack_core.checks import check_pdf_renderer
from qatrack.qatrack_core.utils import pdf_renderer
from qatrack.reports import reports


class TestPdfRendererResolution(TestCase):

    def _renderer_on(self, os_name):
        with mock.patch("qatrack.qatrack_core.utils.os.name", os_name):
            return pdf_renderer()

    @override_settings(PDF_RENDERER="auto")
    def test_auto_prefers_weasyprint_off_windows(self):
        assert self._renderer_on("posix") == "weasyprint"

    @override_settings(PDF_RENDERER="auto")
    def test_auto_picks_chrome_on_windows(self):
        """The point of the setting: a stock Windows install has no pango."""
        assert self._renderer_on("nt") == "chrome"

    @override_settings(PDF_RENDERER="weasyprint")
    def test_windows_can_opt_in(self):
        assert self._renderer_on("nt") == "weasyprint"

    @override_settings(PDF_RENDERER="chrome")
    def test_chrome_can_be_pinned_off_windows(self):
        assert self._renderer_on("posix") == "chrome"

    @override_settings(PDF_RENDERER="  WeasyPrint  ")
    def test_value_is_case_and_space_insensitive(self):
        """local_settings.py is hand-edited; this costs nothing to tolerate."""
        assert self._renderer_on("nt") == "weasyprint"

    @override_settings(PDF_RENDERER="ghostscript")
    def test_unknown_value_falls_back_to_the_platform_default(self):
        """A typo must not take reports down; `check` is where it is reported."""
        assert self._renderer_on("posix") == "weasyprint"
        assert self._renderer_on("nt") == "chrome"

    def test_missing_setting_resolves(self):
        """An upgraded local_settings.py predating the setting still works."""
        with override_settings():
            from django.conf import settings
            del settings.PDF_RENDERER
            assert self._renderer_on("posix") == "weasyprint"
            assert self._renderer_on("nt") == "chrome"


class TestPdfRendererDispatch(TestCase):

    @override_settings(PDF_RENDERER="chrome")
    def test_chrome_is_used_without_trying_weasyprint(self):
        """Chosen, not fallen back to: WeasyPrint must not even be attempted.

        On Windows the old code imported WeasyPrint for every report, failed,
        and logged it - noise about a decision already made.
        """
        with mock.patch("qatrack.reports.reports.chrometopdf") as chrome:
            with mock.patch("qatrack.reports.reports.weasyprint_to_pdf") as weasy:
                chrome.return_value = b"%PDF-"
                assert reports.BaseReport().to_pdf() == b"%PDF-"
        assert chrome.called
        assert not weasy.called

    @override_settings(PDF_RENDERER="weasyprint")
    def test_weasyprint_is_used_when_selected(self):
        with mock.patch("qatrack.reports.reports.chrometopdf") as chrome:
            with mock.patch("qatrack.reports.reports.weasyprint_to_pdf") as weasy:
                weasy.return_value = b"%PDF-weasy"
                assert reports.BaseReport().to_pdf() == b"%PDF-weasy"
        assert not chrome.called

    @override_settings(PDF_RENDERER="weasyprint")
    def test_chrome_still_backs_up_an_opt_in_that_stops_working(self):
        """An install that opts in and later loses pango still gets reports."""
        with mock.patch("qatrack.reports.reports.chrometopdf") as chrome:
            with mock.patch("qatrack.reports.reports.weasyprint_to_pdf") as weasy:
                weasy.side_effect = OSError("cannot load library 'libgobject-2.0-0'")
                chrome.return_value = b"%PDF-chrome"
                assert reports.BaseReport().to_pdf() == b"%PDF-chrome"
        assert chrome.called


class TestPdfRendererCheck(TestCase):

    @override_settings(PDF_RENDERER="ghostscript")
    def test_unknown_value_is_reported(self):
        problems = check_pdf_renderer(None)
        assert len(problems) == 1
        assert problems[0].id == "qatrack.W015"
        assert "ghostscript" in problems[0].msg

    @override_settings(PDF_RENDERER="ghostscript")
    def test_unknown_value_must_not_be_an_error(self):
        """An Error here would stop the task cluster over a typo.

        `manage.py check` failing blocks `migrate`, and `manage.py qcluster`
        exits immediately on a failed check - so every scheduled report and
        notice stops, while the web server carries on rendering reports
        through the fallback. Measured by crane on Windows Server 2022,
        2026-10-19. The severity has to match what the code does, and the code
        falls back.
        """
        problems = check_pdf_renderer(None)
        assert not any(isinstance(p, Error) for p in problems), problems
        assert all(isinstance(p, Warning) for p in problems), problems

    @override_settings(PDF_RENDERER="chrome")
    def test_chrome_is_not_warned_about(self):
        """Chrome is a supported choice, not a degraded one."""
        assert check_pdf_renderer(None) == []

    @override_settings(PDF_RENDERER="weasyprint")
    def test_selecting_an_unimportable_weasyprint_warns(self):
        def explode(name, *args, **kwargs):
            if name == "weasyprint":
                raise OSError("cannot load library 'libgobject-2.0-0'")
            return original(name, *args, **kwargs)

        import builtins
        original = builtins.__import__
        with mock.patch("builtins.__import__", side_effect=explode):
            problems = check_pdf_renderer(None)

        assert len(problems) == 1
        assert isinstance(problems[0], Warning)
        assert problems[0].id == "qatrack.W016"
        assert "libgobject" in problems[0].msg


class TestPaperSizeIsValidatedBeforeAnEngineIsChosen(TestCase):
    """An invalid paper size must not be reported as an engine failure.

    `clean_paper_size` is called by both engines, so the error always
    surfaced - but via the fallback, which logged "WeasyPrint failed on this
    report" with a traceback and then failed the same way inside Chrome. The
    cause named in the log was wrong, and scheduled reports and management
    commands are where anyone would read it. Raised by CodeRabbit.
    """

    @override_settings(PDF_RENDERER="weasyprint")
    def test_no_engine_is_called_for_an_invalid_size(self):
        report = reports.BaseReport()
        report.get_context = lambda: {"paper_size": "a3-ish"}

        with mock.patch("qatrack.reports.reports.chrometopdf") as chrome:
            with mock.patch("qatrack.reports.reports.weasyprint_to_pdf") as weasy:
                with self.assertRaises(ValueError):
                    report.to_pdf()

        assert not chrome.called, "Chrome was asked to render an invalid size"
        assert not weasy.called, "WeasyPrint was asked to render an invalid size"

    @override_settings(PDF_RENDERER="chrome")
    def test_valid_sizes_still_reach_the_engine(self):
        for size in ("letter", "a4", "A4", " letter "):
            with self.subTest(size=size):
                report = reports.BaseReport()
                report.get_context = lambda: {"paper_size": size}
                with mock.patch("qatrack.reports.reports.chrometopdf") as chrome:
                    chrome.return_value = b"%PDF-"
                    report.to_pdf()
                assert chrome.called
                assert chrome.call_args[1]["paper_size"] == size.strip().lower()
