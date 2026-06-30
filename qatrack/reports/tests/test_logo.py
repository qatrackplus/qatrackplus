from unittest import mock

from django.template.loader import get_template
from django.test import TestCase, override_settings

from qatrack.qa.tests import utils
from qatrack.reports import qc
from qatrack.reports.reports import BaseReport
from qatrack.units.models import Site as USite


class TestLogoInReports(TestCase):
    """Test organization logo display in reports across different formats and settings."""

    def setUp(self):
        """Set up test data for logo tests."""
        self.site = USite.objects.create(name="test_site")
        self.unit = utils.create_unit(site=self.site)
        self.utc = utils.create_unit_test_collection(unit=self.unit)
        self.tli = utils.create_test_list_instance(unit_test_collection=self.utc)

    def test_logo_visible_html_report_include_logo_true(self):
        """Test that logo is visible in HTML reports when include_logo=True."""
        rep = qc.TestListInstanceDetailsReport(
            base_opts={'include_logo': True}, report_opts={'unit_test_collection': [self.utc.pk]}
        )
        rep.report_format = "html"
        html_content = rep.to_html()

        # Should contain the visible logo image with correct attributes for HTML
        self.assertIn('alt="Organization Logo"', html_content, "Logo image should be present")
        self.assertIn('class="logo logo-visible"', html_content, "Logo should be visible when include_logo=True")
        self.assertIn('logo.png', html_content, "Logo should reference the correct image file")
        # Should use static path for HTML, not file:// path
        self.assertNotIn('file://', html_content, "Logo should not use file:// path in HTML")

    def test_logo_hidden_html_report_include_logo_false(self):
        """Test that logo is hidden in HTML reports when include_logo=False."""
        rep = qc.TestListInstanceDetailsReport(
            base_opts={'include_logo': False}, report_opts={'unit_test_collection': [self.utc.pk]}
        )
        rep.report_format = "html"
        html_content = rep.to_html()

        # Should contain the hidden logo image
        self.assertIn('alt="Organization Logo"', html_content, "Logo image should be present")
        self.assertIn('class="logo logo-hidden"', html_content, "Logo should be hidden when include_logo=False")
        self.assertIn('logo.png', html_content, "Logo should reference the correct image file")

    @override_settings(STATIC_ROOT='/test/static/root')
    def test_logo_visible_pdf_report_include_logo_true(self):
        """Test that logo uses file:// path in PDF reports when include_logo=True."""
        rep = qc.TestListInstanceDetailsReport(
            base_opts={'include_logo': True}, report_opts={'unit_test_collection': [self.utc.pk]}
        )
        rep.report_format = "pdf"  # Set report_format before calling to_pdf()

        # Mock the PDF generation to avoid WeasyPrint dependency and capture HTML content
        with mock.patch('qatrack.reports.reports.weasyprint_to_pdf') as mock_weasyprint:
            mock_weasyprint.return_value = b'fake pdf content'
            rep.to_pdf()

            # Get the HTML content that would be sent to WeasyPrint
            html_content = mock_weasyprint.call_args[0][0]

        # Should contain the visible logo image with file:// path for PDF
        self.assertIn('alt="Organization Logo"', html_content, "Logo image should be present")
        self.assertIn('class="logo logo-visible"', html_content, "Logo should be visible when include_logo=True")
        self.assertIn(
            'file:///test/static/root/reports/img/logo.png', html_content,
            "Logo should use correct file:// path for PDF"
        )

    @override_settings(STATIC_ROOT='/test/static/root')
    def test_logo_hidden_pdf_report_include_logo_false(self):
        """Test that logo is hidden in PDF reports when include_logo=False."""
        rep = qc.TestListInstanceDetailsReport(
            base_opts={'include_logo': False}, report_opts={'unit_test_collection': [self.utc.pk]}
        )
        rep.report_format = "pdf"  # Set report_format before calling to_pdf()

        # Mock the PDF generation to avoid WeasyPrint dependency and capture HTML content
        with mock.patch('qatrack.reports.reports.weasyprint_to_pdf') as mock_weasyprint:
            mock_weasyprint.return_value = b'fake pdf content'
            rep.to_pdf()

            # Get the HTML content that would be sent to WeasyPrint
            html_content = mock_weasyprint.call_args[0][0]

        # Should contain the hidden logo image
        self.assertIn('alt="Organization Logo"', html_content, "Logo image should be present")
        self.assertIn('class="logo logo-hidden"', html_content, "Logo should be hidden when include_logo=False")
        self.assertIn('file://', html_content, "Logo should use file:// path even when hidden")

    @override_settings(STATIC_ROOT='/test/static/root')
    def test_logo_present_in_pdf(self):
        """Test that logo is present in PDF reports."""
        rep = qc.TestListInstanceDetailsReport(
            base_opts={'include_logo': True}, report_opts={'unit_test_collection': [self.utc.pk]}
        )
        rep.report_format = "pdf"  # Set report_format before calling to_pdf()

        # Mock the PDF generation to capture HTML content
        with mock.patch('qatrack.reports.reports.weasyprint_to_pdf') as mock_weasyprint:
            mock_weasyprint.return_value = b'fake pdf content'
            rep.to_pdf()

            # Get the HTML content that would be sent to WeasyPrint
            html_content = mock_weasyprint.call_args[0][0]

        # Should contain the logo image
        self.assertIn('src="file:///test/static/root/reports/img/logo.png"', html_content, "Logo should be present in PDF")
        self.assertIn('alt="Organization Logo"', html_content, "Logo should have correct alt text")

    def test_logo_present_in_html(self):
        """Test that logo is present in HTML reports."""
        rep = qc.TestListInstanceDetailsReport(
            base_opts={'include_logo': True}, report_opts={'unit_test_collection': [self.utc.pk]}
        )
        rep.report_format = "html"
        html_content = rep.to_html()

        # Should contain the logo image
        self.assertIn('logo.png', html_content, "Logo should be present in HTML")
        self.assertIn('alt="Organization Logo"', html_content, "Logo should have correct alt text")

    def test_header_template_context_for_pdf(self):
        """Test that the header template receives correct context for PDF generation."""
        template = get_template("reports/_header.html")

        # Test PDF context
        context = {
            'for_pdf': 1,
            'include_logo': True,
            'STATIC_ROOT': '/test/static/root',
            'report_title': 'Test Report'
        }

        rendered = template.render(context)

        # Should use file:// path for PDF
        self.assertIn('file:///test/static/root/reports/img/logo.png', rendered, "PDF should use file:// path")

    def test_header_template_context_for_html(self):
        """Test that the header template receives correct context for HTML generation."""
        template = get_template("reports/_header.html")

        # Test HTML context
        context = {'for_pdf': 0, 'include_logo': True, 'report_title': 'Test Report'}

        rendered = template.render(context)

        # Should use static template tag path for HTML
        self.assertNotIn('file://', rendered, "HTML should not use file:// path")
        self.assertIn('logo.png', rendered, "HTML should reference logo file")

    def test_base_report_include_logo_default(self):
        """Test that BaseReport includes logo by default."""
        rep = BaseReport()
        context = rep.get_context()
        self.assertTrue(context['include_logo'], "include_logo should default to True")

    def test_base_report_include_logo_override(self):
        """Test that BaseReport respects include_logo override."""
        rep = BaseReport(base_opts={'include_logo': False})
        context = rep.get_context()
        self.assertFalse(context['include_logo'], "include_logo should be overridden to False")

    def test_logo_css_classes_applied_correctly(self):
        """Test that logo CSS classes are applied correctly based on include_logo setting."""
        template = get_template("reports/_header.html")

        # Test with logo visible
        context = {'include_logo': True, 'for_pdf': 0, 'report_title': 'Test'}
        rendered = template.render(context)
        self.assertIn('class="logo logo-visible"', rendered, "Logo should have visible class when enabled")

        # Test with logo hidden
        context = {'include_logo': False, 'for_pdf': 0, 'report_title': 'Test'}
        rendered = template.render(context)
        self.assertIn('class="logo logo-hidden"', rendered, "Logo should have hidden class when disabled")

    def test_multiple_report_types_logo_consistency(self):
        """Test that logo functionality works consistently across different report types."""
        report_types = [
            (qc.TestListInstanceDetailsReport, {
                'unit_test_collection': [self.utc.pk]
            }),
            (qc.TestListInstanceSummaryReport, {}),
            (qc.AssignedQCReport, {}),
        ]

        for ReportClass, report_opts in report_types:
            with self.subTest(report_type=ReportClass.__name__):
                # Test with logo enabled
                rep = ReportClass(base_opts={'include_logo': True}, report_opts=report_opts)
                rep.report_format = "html"  # Set format to avoid the attribute error
                context = rep.get_context()
                self.assertTrue(context['include_logo'], f"{ReportClass.__name__} should include logo when enabled")

                # Test with logo disabled
                rep = ReportClass(base_opts={'include_logo': False}, report_opts=report_opts)
                rep.report_format = "html"  # Set format to avoid the attribute error
                context = rep.get_context()
                self.assertFalse(
                    context['include_logo'], f"{ReportClass.__name__} should not include logo when disabled"
                )

    def test_logo_file_path_construction(self):
        """Test that logo file paths are constructed correctly for different contexts."""
        template = get_template("reports/_header.html")

        static_root = '/test/static/root'

        # Test PDF path construction
        context = {'for_pdf': 1, 'include_logo': True, 'STATIC_ROOT': static_root, 'report_title': 'Test'}
        rendered = template.render(context)
        self.assertIn(f'file://{static_root}/reports/img/logo.png', rendered, "PDF should use correct file:// path")

        # Test HTML path construction (uses Django static template tag)
        context = {'for_pdf': 0, 'include_logo': True, 'report_title': 'Test'}
        rendered = template.render(context)
        # The exact path will depend on static file handling, but should not contain file://
        self.assertNotIn('file://', rendered, "HTML should not use file:// path")
        self.assertIn('logo.png', rendered, "HTML should reference logo file")

    def test_logo_toggle_functionality_in_forms(self):
        """Test that the include_logo toggle works correctly in form processing."""
        from qatrack.reports.forms import ReportForm

        # Test form with logo enabled (use valid report type and proper field prefixes)
        form_data = {
            'root-title': 'Test Report',
            'root-report_type': 'testlistinstance_details',  # Use a valid report type
            'root-report_format': 'pdf',
            'root-include_logo': True,
        }
        form = ReportForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid with include_logo=True. Errors: {form.errors}")

        # Test form with logo disabled
        form_data['root-include_logo'] = False
        form = ReportForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid with include_logo=False. Errors: {form.errors}")

    def test_logo_no_error_handling(self):
        """Test that no error handling is implemented since we removed fallback messages."""
        template = get_template("reports/_header.html")

        context = {
            'for_pdf': 1,
            'include_logo': True,
            'STATIC_ROOT': '/test/static/root',
            'report_title': 'Test Report'
        }

        rendered = template.render(context)

        # Check that no error handling is present
        self.assertNotIn('onerror=', rendered, "No error handling should be present")
        self.assertNotIn('style="display: none;"', rendered, "No fallback message should be present")

    def test_css_classes_defined(self):
        """Test that all necessary CSS classes are defined in the header template."""
        template = get_template("reports/_header.html")

        context = {'for_pdf': 0, 'include_logo': True, 'report_title': 'Test Report'}

        rendered = template.render(context)

        # Check that CSS classes are defined
        self.assertIn('.logo-hidden', rendered, "logo-hidden class should be defined")
        self.assertIn('.logo-visible', rendered, "logo-visible class should be defined")
        self.assertIn('.logo', rendered, "logo class should be defined")

        # Check CSS properties
        self.assertIn('opacity: 0', rendered, "Hidden logo should have opacity 0")
        self.assertIn('opacity: 1', rendered, "Visible logo should have opacity 1")
        self.assertIn('max-height: 60px', rendered, "Logo should have max height restriction")
