from django.contrib.auth.models import User
from django.test import TestCase

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
