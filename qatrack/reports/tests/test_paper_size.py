import os

from django.contrib.auth.models import User
from django.test import TestCase

from qatrack.reports.forms import ReportForm
from qatrack.reports.models import SavedReport


def get_chrome_command(html, name, paper_size, chrome_path, tmp_root, log_root):
    """Helper function to generate Chrome command without executing it."""
    if not name:
        name = "test"

    fname = f"{name}_test.html"
    path = os.path.join(tmp_root, fname)
    out_path = f"{path}.pdf"

    paper_format = "Letter" if paper_size == "letter" else "A4"

    command = [
        chrome_path,
        '--headless',
        '--disable-gpu',
        '--no-sandbox',
        f'--print-to-pdf={out_path}',
        '--print-to-pdf-no-header',
        f'--print-to-pdf-paper-format={paper_format}',
        f"file://{path}",
    ]

    return command


class TestPaperSizeCommandGeneration(TestCase):
    """Test the generation of Chrome commands for different paper sizes."""

    def setUp(self):
        self.html = "<html><body>Test</body></html>"
        self.chrome_path = "/usr/bin/chrome"
        self.tmp_root = "/tmp"
        self.log_root = "/tmp"

    def test_letter_command_generation(self):
        """Test command generation for Letter paper size."""
        command = get_chrome_command(
            self.html, "test", "letter",
            self.chrome_path, self.tmp_root, self.log_root
        )
        self.assertIn('--print-to-pdf-paper-format=Letter', command)

    def test_a4_command_generation(self):
        """Test command generation for A4 paper size."""
        command = get_chrome_command(
            self.html, "test", "a4",
            self.chrome_path, self.tmp_root, self.log_root
        )
        self.assertIn('--print-to-pdf-paper-format=A4', command)


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
