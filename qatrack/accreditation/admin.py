"""
Django Admin Configuration for Accreditation Models

This module configures the Django admin interface for the accreditation system.

Key Features:
- Export/import functionality
- Organized field layouts with logical grouping
- Search and filtering capabilities
- Audit trail information display
"""

from django.contrib import admin
from django.urls import path
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from qatrack.qatrack_core.admin import SaveUserMixin
from . import models
from . import views


@admin.register(models.Organization)
class OrganizationAdmin(SaveUserMixin, admin.ModelAdmin):
    """
    Admin interface for Organization model.
    
    Provides comprehensive management of accreditation organizations including
    export/import functionality for sharing accreditation data between institutions.
    """
    
    # Display configuration
    list_display = ("name", "country", "website", "document_count", "modified", "modified_by")
    list_filter = ("country", "created", "modified")
    search_fields = ("name", "country", "website")
    readonly_fields = ("created", "created_by", "modified", "modified_by")
    
    # Field organization
    fieldsets = (
        (_("Basic Information"), {
            'fields': ('name', 'country', 'website'),
            'description': _("Core organization details")
        }),
        (_("Audit Information"), {
            'fields': ('created', 'created_by', 'modified', 'modified_by'),
            'classes': ('collapse',),
            'description': _("System-generated audit trail information")
        }),
    )
    
    # Custom methods for display
    def website_link(self, obj):
        """Display website as a clickable link."""
        if obj.website:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.website, obj.website)
        return _("No website")
    website_link.short_description = _("Website")
    website_link.admin_order_field = 'website'
    
    def document_count(self, obj):
        """Display the number of documents for this organization."""
        return obj.documents.count()
    document_count.short_description = _("Documents")
    document_count.admin_order_field = 'documents__count'
    
    # Custom URLs for export/import functionality
    def get_urls(self):
        """Add custom URLs for export and import functionality."""
        urls = super().get_urls()
        custom_urls = [
            path(
                'export-accreditation/',
                self.admin_site.admin_view(views.ExportAccreditation.as_view()),
                name='organization_export'
            ),
            path(
                'import-accreditation/',
                self.admin_site.admin_view(views.ImportAccreditation.as_view()),
                name='organization_import'
            ),
        ]
        return custom_urls + urls


@admin.register(models.Document)
class DocumentAdmin(SaveUserMixin, admin.ModelAdmin):
    """
    Admin interface for Document model.
    
    Manages reference documents and standards from accreditation organizations,
    providing export/import capabilities for sharing document collections.
    """
    
    # Display configuration
    list_display = ("name", "organization", "tag_name", "doi", "year", "requirement_count", "modified", "modified_by")
    list_filter = ("organization", "year", "created", "modified")
    search_fields = ("name", "organization__name", "tag_name", "doi")
    readonly_fields = ("created", "created_by", "modified", "modified_by")
    
    # Field organization
    fieldsets = (
        (_("Document Information"), {
            'fields': ('organization', 'name', 'tag_name'),
            'description': _("Core document identification")
        }),
        (_("Publication Details"), {
            'fields': ('doi', 'year', 'pdf_file'),
            'description': _("Academic and publication information")
        }),
        (_("Audit Information"), {
            'fields': ('created', 'created_by', 'modified', 'modified_by'),
            'classes': ('collapse',),
            'description': _("System-generated audit trail information")
        }),
    )
    
    # Custom methods for display
    def requirement_count(self, obj):
        """Display the number of requirements in this document."""
        return obj.requirements.count()
    requirement_count.short_description = _("Requirements")
    requirement_count.admin_order_field = 'requirements__count'
    
    # Custom URLs for export/import functionality
    def get_urls(self):
        """Add custom URLs for export and import functionality."""
        urls = super().get_urls()
        custom_urls = [
            path(
                'export-accreditation/',
                self.admin_site.admin_view(views.ExportAccreditation.as_view()),
                name='document_export'
            ),
            path(
                'import-accreditation/',
                self.admin_site.admin_view(views.ImportAccreditation.as_view()),
                name='document_import'
            ),
        ]
        return custom_urls + urls


@admin.register(models.Requirement)
class RequirementAdmin(SaveUserMixin, admin.ModelAdmin):
    """
    Admin interface for Requirement model.
    
    Manages individual accreditation requirements and QA test procedures,
    providing comprehensive filtering and search capabilities for compliance management.
    """
    
    # Display configuration
    list_display = ("tag_name", "document", "organization", "periodicity", "compliance_level", "energy", "requirement_class")
    list_filter = (
        "document__organization", 
        "document", 
        "periodicity", 
        "compliance_level", 
        "energy", 
        "requirement_class",
        "international_recommendation",
        "created",
        "modified"
    )
    search_fields = ("tag_name", "document__name", "document__organization__name", "tolerance")
    readonly_fields = ("created", "created_by", "modified", "modified_by")
    
    # Field organization with logical grouping
    fieldsets = (
        (_("Requirement Identification"), {
            'fields': ('document', 'tag_name'),
            'description': _("Core requirement identification")
        }),
        (_("Performance Specifications"), {
            'fields': ('periodicity', 'tolerance'),
            'description': _("How often and what criteria to meet")
        }),
        (_("Classification"), {
            'fields': ('compliance_level', 'energy', 'requirement_class'),
            'description': _("Categorization and classification")
        }),
        (_("International Status"), {
            'fields': ('international_recommendation',),
            'description': _("International applicability and requirements")
        }),
        (_("Audit Information"), {
            'fields': ('created', 'created_by', 'modified', 'modified_by'),
            'classes': ('collapse',),
            'description': _("System-generated audit trail information")
        }),
    )
    
    # Custom methods for display
    def organization(self, obj):
        """Display the organization name for easy reference."""
        return obj.document.organization.name
    organization.short_description = _("Organization")
    organization.admin_order_field = 'document__organization__name'
    
    # Future enhancement considerations
    # TODO: Consider adding custom admin actions for bulk operations on requirements
    # TODO: Consider adding inline editing for requirements within documents
    # TODO: Consider adding requirement templates for common QA procedures
    # TODO: Consider adding compliance tracking and reporting features
    