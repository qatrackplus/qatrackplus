"""
Accreditation Models for QATrack+

This module defines the core models for managing medical physics accreditation requirements.
The system follows a hierarchical structure: Organization -> Document -> Requirement.

Key Features:
- Organizations: Represent accreditation bodies
- Documents: Reference materials and standards from organizations
- Requirements: Specific QA tests

Design Principles:
- Uses TestPackMixin for import/export functionality
- Implements natural keys for data integrity
- Supports internationalization (i18n)
"""

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from qatrack.qa.testpack import TestPackMixin


class Organization(models.Model, TestPackMixin):
    """
    Represents an accreditation or regulatory organization.
    
    Attributes:
        name: Official name of the organization
        country: Country where the organization is based
        website: Official website URL for reference
        created/modified: Audit trail timestamps
        created_by/modified_by: User who created/modified the record
    """
    
    NK_FIELDS = ['name']
    
    name = models.CharField(
        max_length=255,
        verbose_name=_("Organization Name"),
        help_text=_("Official name of the accreditation organization"),
        unique=True,  # Prevent duplicate organization names
    )
    country = models.CharField(
        max_length=100,
        verbose_name=_("Country"),
        help_text=_("Country where the organization is based"),
    )
    website = models.URLField(
        verbose_name=_("Website"),
        help_text=_("Official website URL of the organization for reference"),
        blank=True,
        null=True,  # Allow null for organizations without websites
    )
    
    # Audit trail fields
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        related_name="organization_created",
        verbose_name=_("Created By"),
    )
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        related_name="organization_modified",
        verbose_name=_("Modified By"),
    )

    class Meta:
        ordering = ("name",)
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        # Note: These indexes help with faster searches by name and country
        # They're especially useful when you have many organizations
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['country']),
        ]

    def __str__(self):
        """Return the organization name for display."""
        return self.name
    
    def clean(self):
        """Validate the organization data."""
        super().clean()
        if self.name:
            self.name = self.name.strip()
        if self.country:
            self.country = self.country.strip()
    
    @classmethod
    def get_testpack_fields(cls):
        """
        Define which fields are included in testpack export.
        
        Excludes internal fields like IDs and audit trail information.
        """
        exclude = ["id", "created", "created_by", "modified", "modified_by"]
        return [f.name for f in cls._meta.concrete_fields if f.name not in exclude]
    
    def get_testpack_dependencies(self):
        """
        Organizations have no dependencies
        
        Returns:
            Empty list since organizations don't depend on other models.
        """
        return []
    
    def natural_key(self):
        """
        Natural key for the organization.
        
        A natural key is a way to identify records using business data instead of database IDs.
        For organizations, we use the name as the natural key.
        
        Returns:
            Tuple containing the organization name for unique identification.
            A tuple is an immutable sequence of values, like a list but can't be changed.
        """
        return (self.name,)


class Document(models.Model, TestPackMixin):
    """
    Represents a reference document
    
    Documents contain the actual accreditation requirements and guidelines.
    They are linked to organizations and can contain multiple requirements.
    
    Attributes:
        organization: The organization that published this document
        name: Title or name of the document
        tag_name: Short identifier for the document
        doi: Digital Object Identifier for academic reference
        year: Publication year
        pdf_file: Optional file attachment
        created/modified: Audit trail timestamps
        created_by/modified_by: User who created/modified the record
    """
    
    NK_FIELDS = ['organization', 'name']
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_("Organization"),
        help_text=_("Organization that published this document"),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Document Name"),
        help_text=_("Title or name of the document"),
    )
    tag_name = models.CharField(
        max_length=100,
        verbose_name=_("Tag Name"),
        help_text=_("Short identifier/tag for the document"),
    )
    doi = models.CharField(
        max_length=255,
        verbose_name=_("DOI"),
        help_text=_("Digital Object Identifier for reference"),
        blank=True,
        null=True,
    )
    year = models.PositiveIntegerField(
        verbose_name=_("Year"),
        help_text=_("Year when the document was published"),
        null=True,
        blank=True,
    )
    pdf_file = models.FileField(
        upload_to='accreditation/documents/',
        verbose_name=_("File"),
        help_text=_("Document file"),
        blank=True,
        null=True,
    )
    
    # Audit trail fields
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        related_name="document_created",
        verbose_name=_("Created By"),
    )
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        related_name="document_modified",
        verbose_name=_("Modified By"),
    )

    class Meta:
        ordering = ("organization", "name")
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        # This ensures that within each organization, document names must be unique
        # This helps prevent accidentally creating duplicate documents with the same name
        # in the same organization
        unique_together = [['organization', 'name']]
        # Add indexes for better query performance
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['tag_name']),
            models.Index(fields=['year']),
        ]

    def __str__(self):
        """Return organization and document name for display."""
        return f"{self.organization.name} - {self.name}"
    
    def clean(self):
        """Validate the document data."""
        super().clean()
        if self.name:
            self.name = self.name.strip()
        if self.tag_name:
            self.tag_name = self.tag_name.strip()
        if self.doi:
            self.doi = self.doi.strip()
    
    @classmethod
    def get_testpack_fields(cls):
        """
        Define which fields are included in testpack export.
        
        Excludes internal fields like IDs and audit trail information.
        """
        exclude = ["id", "created", "created_by", "modified", "modified_by"]
        return [f.name for f in cls._meta.concrete_fields if f.name not in exclude]
    
    def get_testpack_dependencies(self):
        """
        Documents depend on their organization.
        
        Returns:
            List of dependency tuples for testpack export.
        """
        return [
            (Organization, [self.organization]),
        ]
    
    def natural_key(self):
        """
        Natural key for the document.
        
        Returns:
            Tuple containing organization natural key and document name.
        """
        return (self.organization.natural_key(), self.name)


class Requirement(models.Model, TestPackMixin):
    """
    Represents a specific accreditation requirement.
    
    Requirements are the core entities that define what needs to be tested,
    how often, and what the acceptance criteria are. They are linked to
    documents and inherit organization context.
    
    Attributes:
        document: The document that contains this requirement
        tag_name: Unique identifier for the requirement
        periodicity: How often the requirement should be performed
        tolerance: Acceptance criteria and tolerances
        compliance_level: Whether the requirement is mandatory/recommended/optional
        energy: Type of radiation energy (photon/electron)
        requirement_class: Classification of the requirement type
        international_recommendation: International requirement status
        created/modified: Audit trail timestamps
        created_by/modified_by: User who created/modified the record
    """
    
    NK_FIELDS = ['document', 'tag_name']
    
    # Choice field definitions with comprehensive options
    PERIODICITY_CHOICES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('bi_annually', _('Bi-Annually')),
        ('annually', _('Annually')),
    ]
    
    COMPLIANCE_LEVEL_CHOICES = [
        ('mandatory', _('Mandatory')),
        ('recommended', _('Recommended')),
        ('optional', _('Optional')),
    ]
    
    ENERGY_CHOICES = [
        ('photon', _('Photon')),
        ('electron', _('Electron')),
    ]
    
    REQUIREMENT_CLASS_CHOICES = [
        ('mechanical_imaging', _('Mechanical Imaging')),
        ('dosimetry_relative', _('Dosimetry - Relative')),
        ('dosimetry_absolute', _('Dosimetry - Absolute')),
    ]
    
    INTERNATIONAL_CHOICES = [
        ('internationally_required', _('Internationally Required')),
        ('internationally_optional', _('Internationally Optional')),
    ]
    
    # Core requirement fields
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='requirements',
        verbose_name=_("Document"),
        help_text=_("Document that contains this requirement"),
    )
    tag_name = models.CharField(
        max_length=100,
        verbose_name=_("Requirement Tag Name"),
        help_text=_("Unique identifier/tag for the requirement"),
    )
    periodicity = models.CharField(
        max_length=20,
        choices=PERIODICITY_CHOICES,
        verbose_name=_("Periodicity"),
        help_text=_("Frequency of requirement performance"),
        default='monthly',
    )
    tolerance = models.CharField(
        max_length=255,
        verbose_name=_("Tolerance"),
        help_text=_("Acceptance criteria and tolerance specifications"),
        blank=True,
    )
    compliance_level = models.CharField(
        max_length=20,
        choices=COMPLIANCE_LEVEL_CHOICES,
        verbose_name=_("Compliance Level"),
        help_text=_("Whether this requirement is mandatory, recommended, or optional"),
        default='mandatory',
    )
    energy = models.CharField(
        max_length=20,
        choices=ENERGY_CHOICES,
        verbose_name=_("Energy"),
        help_text=_("Energy type for this requirement"),
        default='photon',
    )
    requirement_class = models.CharField(
        max_length=30,
        choices=REQUIREMENT_CLASS_CHOICES,
        verbose_name=_("Requirement Class"),
        help_text=_("Classification of this requirement"),
        default='mechanical_imaging',
    )
    international_recommendation = models.CharField(
        max_length=30,
        choices=INTERNATIONAL_CHOICES,
        verbose_name=_("International Recommendation"),
        help_text=_("International requirement status"),
        default='internationally_optional',
    )
    
    # Audit trail fields
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        related_name="requirement_created",
        verbose_name=_("Created By"),
    )
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        related_name="requirement_modified",
        verbose_name=_("Modified By"),
    )

    class Meta:
        ordering = ("document", "tag_name")
        verbose_name = _("Requirement")
        verbose_name_plural = _("Requirements")
        # This ensures that within each document, requirement tag names must be unique
        # This prevents having two requirements with the same tag name in the same document
        unique_together = [['document', 'tag_name']]
        # Add indexes for better query performance
        indexes = [
            models.Index(fields=['document', 'tag_name']),
            models.Index(fields=['periodicity']),
            models.Index(fields=['compliance_level']),
            models.Index(fields=['energy']),
            models.Index(fields=['requirement_class']),
        ]

    def __str__(self):
        """Return document name and requirement tag for display."""
        return f"{self.document.name} - {self.tag_name}"
    
    def clean(self):
        """Validate the requirement data."""
        super().clean()
        if self.tag_name:
            self.tag_name = self.tag_name.strip()
        if self.tolerance:
            self.tolerance = self.tolerance.strip()
    
    @classmethod
    def get_testpack_fields(cls):
        """
        Define which fields are included in testpack export.
        
        Excludes internal fields like IDs and audit trail information.
        """
        exclude = ["id", "created", "created_by", "modified", "modified_by"]
        return [f.name for f in cls._meta.concrete_fields if f.name not in exclude]
    
    def get_testpack_dependencies(self):
        """
        Requirements depend on their document and organization.
        
        Returns:
            List of dependency tuples for testpack export.
        """
        return [
            (Document, [self.document]),
            (Organization, [self.document.organization]),
        ]
    
    def natural_key(self):
        """
        Natural key for the requirement.
        
        Returns:
            Tuple containing document natural key and requirement tag name.
        """
        return (self.document.natural_key(), self.tag_name)
