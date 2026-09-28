
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from qatrack.qatrack_core.utils import set_paper_size
from qatrack.reports.forms import ReportForm
from qatrack.reports.models import SavedReport


class TestPaperSizeCss(TestCase):
    """Chrome has no working paper size switch, so the size has to be set in
    CSS.  These assert against the real helper rather than a copy of it: the
    previous version of this module tested a local reimplementation of the
    command builder, so it kept passing while production silently emitted
    Letter for every report."""

    def setUp(self):
        self.html = "<html><head><style>p { color: red; }</style></head><body>Test</body></html>"

    def test_letter_rule_added(self):
        assert "@page { size: letter; }" in set_paper_size(self.html, "letter")

    def test_a4_rule_added(self):
        assert "@page { size: a4; }" in set_paper_size(self.html, "a4")

    def test_rule_goes_last_in_head(self):
        """It has to come after reports/pdf.css to win the cascade."""
        out = set_paper_size(self.html, "a4")
        assert out.index("p { color: red; }") < out.index("@page { size: a4; }") < out.index("</head>")

    def test_case_is_normalised(self):
        assert "@page { size: a4; }" in set_paper_size(self.html, "A4")

    def test_document_body_is_untouched(self):
        assert "<body>Test</body>" in set_paper_size(self.html, "a4")

    def test_fragment_without_head_still_gets_rule(self):
        out = set_paper_size("<p>fragment</p>", "a4")
        assert out.startswith("<style>@page { size: a4; }</style>")
        assert out.endswith("<p>fragment</p>")

    def test_only_first_head_is_targeted(self):
        out = set_paper_size("<html><head></head><body></head></body></html>", "letter")
        assert out.count("@page { size: letter; }") == 1


class TestPaperSizeDefaults(TestCase):
    """Test default paper size settings in models and forms."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

    def test_saved_report_default_paper_size(self):
        """Test that SavedReport defaults to letter paper size."""
        report = SavedReport.objects.create(
            title="Test Report",
            report_type="testlistinstance_summary",
            report_format="pdf",
            created_by=self.user,
            modified_by=self.user
        )
        self.assertEqual(report.paper_size, 'letter')

    def test_report_form_default_paper_size(self):
        """Test that ReportForm defaults to letter paper size."""
        form = ReportForm()
        self.assertEqual(form.fields['paper_size'].initial, 'letter')

    def test_report_form_paper_size_choices(self):
        """Test that form includes both paper size options."""
        form = ReportForm()
        choices = [choice[0] for choice in form.fields['paper_size'].choices]
        self.assertIn('letter', choices)
        self.assertIn('a4', choices)


class TestCleanPaperSize(TestCase):
    """The value is interpolated into a CSS declaration, so it is validated.

    An unexpected string does not fail loudly - it changes the rendered
    document - which is the wrong failure mode for a QC record.
    """

    def test_valid_sizes_pass_through_normalised(self):
        from qatrack.qatrack_core.utils import clean_paper_size

        assert clean_paper_size("letter") == "letter"
        assert clean_paper_size("A4") == "a4"
        assert clean_paper_size(" Letter ") == "letter"

    def test_empty_falls_back_to_letter(self):
        from qatrack.qatrack_core.utils import clean_paper_size

        assert clean_paper_size("") == "letter"
        assert clean_paper_size(None) == "letter"

    def test_unexpected_value_is_rejected(self):
        from qatrack.qatrack_core.utils import clean_paper_size

        with self.assertRaises(ValueError):
            clean_paper_size("legal")

    def test_css_injection_is_rejected(self):
        from qatrack.qatrack_core.utils import clean_paper_size

        with self.assertRaises(ValueError):
            clean_paper_size("letter; } body { display: none } @page {")


class TestChromeFailureReporting(TestCase):
    """A failed report should say which thing failed.

    Neither the exit status nor the output file was checked, so a browser that
    ran and produced nothing surfaced as "executable not found" - naming the
    one component that was working. See #835, where the reporter had a browser
    that ran the command by hand but silently failed under the service.
    """

    # Never executed: the tests below that use it mock subprocess.call.  It only
    # has to be a non-empty CHROME_PATH so the missing-setting branch is not hit.
    fake_browser = "a-browser-that-is-never-run"

    def test_missing_chrome_path_names_the_setting(self):
        from qatrack.qatrack_core.utils import ChromeNotFound, chrometopdf

        with override_settings(CHROME_PATH=""):
            with self.assertRaises(ChromeNotFound) as caught:
                chrometopdf("<html><body>x</body></html>")
        assert "CHROME_PATH" in str(caught.exception)

    def test_unrunnable_executable_is_reported_as_not_found(self):
        from qatrack.qatrack_core.utils import ChromeNotFound, chrometopdf

        with override_settings(CHROME_PATH="/nonexistent/browser"):
            with self.assertRaises(ChromeNotFound):
                chrometopdf("<html><body>x</body></html>")

    def test_a_browser_that_produces_no_pdf_is_not_reported_as_missing(self):
        """The #835 case: it runs, it exits 0, there is no PDF.

        The exit status is faked rather than borrowed from /bin/true, which does
        not exist on Windows - where #835 was reported and where CI also runs.
        """
        from unittest import mock

        from qatrack.qatrack_core import utils

        with override_settings(CHROME_PATH=self.fake_browser):
            with mock.patch.object(utils.subprocess, "call", return_value=0):
                with self.assertRaises(utils.ChromePdfFailed) as caught:
                    utils.chrometopdf("<html><body>x</body></html>")
        assert not isinstance(caught.exception, utils.ChromeNotFound)
        assert "wrote no PDF" in str(caught.exception)

    def test_a_failed_run_leaves_no_partial_pdf_behind(self):
        """A browser can exit non-zero *after* writing part of a PDF.

        The cleanup used to unlink `out_file.name`, and `out_file` is only
        assigned once both failure branches have passed - so on every failed run
        that had written something, the partial file stayed in TMP_REPORT_ROOT.
        Reports are generated on a schedule, so that accumulates unattended.
        """
        import os
        from unittest import mock

        from qatrack.qatrack_core import utils

        written = []

        def exit_nonzero_after_writing(command, **kwargs):
            # mimic a browser that produced something and then failed
            out = [a.split("=", 1)[1] for a in command if a.startswith("--print-to-pdf=")][0]
            with open(out, "wb") as f:
                f.write(b"%PDF-partial")
            written.append(out)
            return 1

        with override_settings(CHROME_PATH=self.fake_browser):
            with mock.patch.object(utils.subprocess, "call", side_effect=exit_nonzero_after_writing):
                with self.assertRaises(utils.ChromePdfFailed):
                    utils.chrometopdf("<html><body>x</body></html>")

        assert written, "the fake browser never wrote anything"
        for path in written:
            assert not os.path.exists(path), (
                "a partial PDF was left behind at %s after a failed run" % path
            )

    def test_nonzero_exit_is_reported_with_the_log_location(self):
        from unittest import mock

        from qatrack.qatrack_core import utils

        with override_settings(CHROME_PATH=self.fake_browser):
            with mock.patch.object(utils.subprocess, "call", return_value=1):
                with self.assertRaises(utils.ChromePdfFailed) as caught:
                    utils.chrometopdf("<html><body>x</body></html>")
        assert "report-stderr.txt" in str(caught.exception)


class TestChromeCommandQuoting(TestCase):
    """The browser command is handed to subprocess as a sequence.

    On Windows it used to be flattened with ' '.join() before the call.
    Nothing in that join quotes anything, and every Chrome location
    settings.py probes lives under "C:\\Program Files (x86)", so what reached
    CreateProcess named an executable "C:\\Program" with the remainder as
    arguments.  Windows' prefix-guessing fallback covered that up for the
    executable; it does not extend to --print-to-pdf=, so a TMP_REPORT_ROOT
    under a profile directory containing a space came apart without an error.
    """

    def _capture_command(self, chrome_path, tmp_report_root=None):
        """Run chrometopdf far enough to see what it would have executed."""
        import subprocess
        from unittest import mock

        from qatrack.qatrack_core.utils import ChromePdfFailed, chrometopdf

        captured = {}

        def fake_call(command, *args, **kwargs):
            captured['command'] = command
            return 0

        overrides = {'CHROME_PATH': chrome_path}
        if tmp_report_root:
            overrides['TMP_REPORT_ROOT'] = tmp_report_root

        with override_settings(**overrides):
            with mock.patch.object(subprocess, "call", fake_call):
                # No PDF is written, because nothing ran -- the command is
                # what is under test, not its result.
                with self.assertRaises(ChromePdfFailed):
                    chrometopdf("<html><body>x</body></html>")

        return captured['command']

    def test_command_is_a_sequence_not_a_string(self):
        command = self._capture_command("/usr/bin/chromium")
        assert isinstance(command, list | tuple), repr(command)

    def test_executable_with_spaces_stays_one_argument(self):
        chrome = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        command = self._capture_command(chrome)
        assert command[0] == chrome

    def test_executable_with_spaces_is_quoted_for_windows(self):
        """What subprocess would actually hand to CreateProcess."""
        import subprocess

        chrome = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        line = subprocess.list2cmdline(self._capture_command(chrome))
        assert line.startswith('"%s"' % chrome), line

    def test_output_path_with_spaces_is_quoted_for_windows(self):
        """The half no CreateProcess heuristic rescues."""
        import subprocess
        import tempfile

        root = tempfile.mkdtemp(suffix=" reports")
        command = self._capture_command("/usr/bin/chromium", tmp_report_root=root)

        out_arg = [a for a in command if a.startswith("--print-to-pdf=")]
        assert len(out_arg) == 1, command
        assert " " in out_arg[0], out_arg
        assert '"%s"' % out_arg[0] in subprocess.list2cmdline(command)

    def test_missing_chrome_path_is_caught_before_the_command_is_built(self):
        """CHROME_PATH of None used to raise TypeError out of the join."""
        from qatrack.qatrack_core.utils import ChromeNotFound, chrometopdf

        with override_settings(CHROME_PATH=None):
            with self.assertRaises(ChromeNotFound):
                chrometopdf("<html><body>x</body></html>")
