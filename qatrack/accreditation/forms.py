"""
Forms for Accreditation Import/Export Functionality

This module defines the forms used for importing and exporting accreditation data
in the QATrack+ system. The forms handle data validation, user input processing,
and integration with the accreditation pack system.

Key Features:
- Export form for selecting organizations and documents
- Import form for uploading accreditation pack files
- Integration with JavaScript for dynamic table selection
- Support for .accr files (QATrack+ accreditation format)

Note: An "accreditation pack" (.accr) file is QATrack+'s format for packaging and
sharing accreditation data between different installations. It contains your accreditation data
along with metadata about when it was created and what it contains.
"""

from django import forms
from django.utils.translation import gettext_lazy as _


class ExportAccreditationForm(forms.Form):
    """
    Form for exporting accreditation data to an accreditation pack file.
    
    This form allows users to select which organizations and documents to export,
    along with optional metadata like name and description.
    
    Fields:
        organizations: Hidden field containing selected organization IDs or "all"
        documents: Hidden field containing selected document IDs or "all"
        name: User-defined name for the export file
        description: Optional description of the export contents
    """
    
    # Hidden fields populated by JavaScript table selection
    organizations = forms.CharField(
        widget=forms.HiddenInput(), 
        required=False,
        help_text=_("Selected organizations for export (populated automatically)")
    )
    documents = forms.CharField(
        widget=forms.HiddenInput(), 
        required=False,
        help_text=_("Selected documents for export (populated automatically)")
    )
    
    # User-defined metadata
    name = forms.CharField(
        max_length=100,
        label=_('Export Name'),
        help_text=_('Name for your export file'),
        initial='accreditation_export',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter export name...',
            'class': 'form-control'
        })
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'placeholder': 'Describe what this export contains...',
            'class': 'form-control'
        }),
        required=False,
        label=_('Description'),
        help_text=_('Optional description of this export for future reference')
    )
    
    def clean_organizations(self):
        """
        Validate and parse the organizations field.
        
        Converts the hidden field value into a QuerySet of Organization objects.
        Supports "all" for selecting all organizations or comma-separated IDs.
        
        Returns:
            QuerySet of Organization objects or empty QuerySet if none selected
            
        Raises:
            ValidationError: If the data format is invalid
        """
        organizations_data = self.cleaned_data['organizations'].strip()
        
        if not organizations_data:
            return self._get_empty_organization_queryset()
        
        if organizations_data == "all":
            return self._get_all_organizations()
        
        # Parse comma-separated IDs
        try:
            org_ids = [int(id.strip()) for id in organizations_data.split(",") if id.strip()]
            if not org_ids:
                return self._get_empty_organization_queryset()
            
            return self._get_organizations_by_ids(org_ids)
            
        except ValueError:
            raise forms.ValidationError(_("Invalid organization ID format. Please refresh and try again."))
    
    def clean_documents(self):
        """
        Validate and parse the documents field.
        
        Converts the hidden field value into a QuerySet of Document objects.
        Supports "all" for selecting all documents or comma-separated IDs.
        
        Returns:
            QuerySet of Document objects or empty QuerySet if none selected
            
        Raises:
            ValidationError: If the data format is invalid
        """
        documents_data = self.cleaned_data['documents'].strip()
        
        if not documents_data:
            return self._get_empty_document_queryset()
        
        if documents_data == "all":
            return self._get_all_documents()
        
        # Parse comma-separated IDs
        try:
            doc_ids = [int(id.strip()) for id in documents_data.split(",") if id.strip()]
            if not doc_ids:
                return self._get_empty_document_queryset()
            
            return self._get_documents_by_ids(doc_ids)
            
        except ValueError:
            raise forms.ValidationError(_("Invalid document ID format. Please refresh and try again."))
    
    def clean(self):
        """
        Validate the overall form data.
        
        Ensures that at least one organization or document is selected for export.
        This prevents creating empty export files.
        
        Returns:
            Cleaned form data
            
        Raises:
            ValidationError: If no items are selected for export
        """
        cleaned_data = super().clean()
        
        # Check if either field has selected items (QuerySets should exist and not be empty)
        orgs_selected = cleaned_data.get('organizations')
        docs_selected = cleaned_data.get('documents')
        
        orgs_has_content = orgs_selected and orgs_selected.exists()
        docs_has_content = docs_selected and docs_selected.exists()
        
        if not orgs_has_content and not docs_has_content:
            raise forms.ValidationError(
                _("You must select at least one Organization or Document for Export. "
                  "Please use the tables above to make your selection.")
            )
        
        return cleaned_data
    
    def _get_empty_organization_queryset(self):
        """Return an empty QuerySet for organizations."""
        from .models import Organization
        return Organization.objects.none()
    
    def _get_all_organizations(self):
        """Return all organizations."""
        from .models import Organization
        return Organization.objects.all()
    
    def _get_organizations_by_ids(self, org_ids):
        """Return organizations filtered by IDs."""
        from .models import Organization
        return Organization.objects.filter(id__in=org_ids)
    
    def _get_empty_document_queryset(self):
        """Return an empty QuerySet for documents."""
        from .models import Document
        return Document.objects.none()
    
    def _get_all_documents(self):
        """Return all documents."""
        from .models import Document
        return Document.objects.all()
    
    def _get_documents_by_ids(self, doc_ids):
        """Return documents filtered by IDs."""
        from .models import Document
        return Document.objects.filter(id__in=doc_ids)


class ImportAccreditationForm(forms.Form):
    """
    Form for importing accreditation data from an accreditation pack file.
    
    This form handles file uploads and provides fields for selecting which
    organizations and documents to import.
    
    Fields:
        accreditation_file: File upload field for .accr files
        accreditation_data: Hidden field containing parsed file content
        organizations: Hidden field for selected organizations to import
        documents: Hidden field for selected documents to import
    """
    
    # File upload field - support .accr files for consistency
    accreditation_file = forms.FileField(
        label=_('Accreditation Pack File'),
        help_text=_('Select a .accr file containing accreditation data. '
                   'Maximum file size: 10MB'),
        widget=forms.FileInput(attrs={
            'accept': '.accr',
            'class': 'form-control-file',
            'data-max-size': '10MB'
        }),
        error_messages={
            'required': _('Please select a file to import.'),
            'invalid': _('Please select a valid file.'),
        }
    )
    
    # Hidden fields for JavaScript integration
    accreditation_data = forms.CharField(
        widget=forms.HiddenInput(), 
        required=False,
        help_text=_("Parsed content of the uploaded file (populated automatically)")
    )
    organizations = forms.CharField(
        widget=forms.HiddenInput(), 
        required=False,
        help_text=_("Selected organizations for import (populated automatically)")
    )
    documents = forms.CharField(
        widget=forms.HiddenInput(), 
        required=False,
        help_text=_("Selected documents for import (populated automatically)")
    )
    requirements = forms.CharField(
        widget=forms.HiddenInput(), 
        required=False,
        help_text=_("Selected requirements for import (populated automatically)")
    )
    
    def clean_accreditation_file(self):
        """
        Validate the uploaded file.
        
        Checks file type, size, and basic format requirements.
        
        Returns:
            The validated file object
            
        Raises:
            ValidationError: If the file is invalid or too large
        """
        file = self.cleaned_data.get('accreditation_file')
        
        if not file:
            raise forms.ValidationError(_('No file was uploaded.'))
        
        # Only accept .accr files for consistency
        if not file.name.endswith('.accr'):
            raise forms.ValidationError(
                _('File must be a .accr file. Received: %(extension)s'),
                params={'extension': file.name.split('.')[-1] if '.' in file.name else 'unknown'}
            )
        
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if file.size > max_size:
            raise forms.ValidationError(
                _('File size must be less than 10MB. Current size: %(size)s'),
                params={'size': self._format_file_size(file.size)}
            )
        
        # Check if file is empty
        if file.size == 0:
            raise forms.ValidationError(_('The uploaded file is empty.'))
        
        return file
    
    def _format_file_size(self, size_bytes):
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
