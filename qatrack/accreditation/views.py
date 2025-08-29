"""
Views for Accreditation Import/Export Functionality

This module provides the core views for importing and exporting accreditation data
in the QATrack+ system.
"""

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
import json
import logging
from collections import Counter

from .models import Organization, Document, Requirement
from .forms import ExportAccreditationForm, ImportAccreditationForm

logger = logging.getLogger(__name__)


class ExportAccreditation(PermissionRequiredMixin, FormView):
    """View for exporting accreditation data"""
    
    permission_required = 'accreditation.change_requirement'
    form_class = ExportAccreditationForm
    template_name = "admin/accreditation/export.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Export Accreditation Data")
        context['organizations'] = Organization.objects.all()
        context['documents'] = Document.objects.select_related('organization').all()
        return context
    
    def form_valid(self, form):
        try:
            orgs = form.cleaned_data['organizations']
            docs = form.cleaned_data['documents']
            desc = form.cleaned_data['description']
            user = self.request.user
            name = form.cleaned_data['name']
            
            # Build export data based on what was selected
            export_data = {
                'objects': {
                    'organizations': [],
                    'documents': [],
                    'requirements': [],
                },
                'meta': {
                    'version': '1.0',
                    'datetime': str(user.date_joined),
                    'description': desc,
                    'contact': user.username,
                    'name': name,
                    'host_url': self.request.build_absolute_uri('/')[:-1],
                    'website': 'https://qatrackplus.com',
                },
            }
            
            # If organizations are selected, include all their documents and requirements
            if orgs.exists():
                for org in orgs:
                    try:
                        org_data = org.to_testpack()
                        export_data['objects']['organizations'].append(org_data)
                        
                        # Get all documents for this organization
                        org_docs = Document.objects.filter(organization=org)
                        for doc in org_docs:
                            try:
                                doc_data = doc.to_testpack()
                                export_data['objects']['documents'].append(doc_data)
                                
                                # Get all requirements for this document
                                doc_reqs = Requirement.objects.filter(document=doc)
                                for req in doc_reqs:
                                    try:
                                        req_data = req.to_testpack()
                                        export_data['objects']['requirements'].append(req_data)
                                    except Exception as e:
                                        logger.error(f"Failed to add requirement {req.tag_name}: {str(e)}")
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        pass
                
            # If documents are selected, include their organization and all requirements
            if docs.exists():
                for doc in docs:
                    # Only add document if not already added via organization
                    doc_already_added = False
                    for existing_doc in export_data['objects']['documents']:
                        if isinstance(existing_doc, str):
                            # Parse the JSON string to check
                            try:
                                doc_obj = json.loads(existing_doc)
                                # Check if document with same name and organization already exists
                                existing_key = doc_obj.get('key', [None, None])
                                if (isinstance(existing_key, list) and 
                                    len(existing_key) >= 2 and
                                    existing_key[0] == [doc.organization.name] and 
                                    existing_key[1] == doc.name):
                                    doc_already_added = True
                                    break
                            except:
                                pass
                        elif isinstance(existing_doc, dict):
                            # Check if document with same name and organization already exists
                            existing_key = existing_doc.get('key', [None, None])
                            if (isinstance(existing_key, list) and 
                                len(existing_key) >= 2 and
                                existing_key[0] == [doc.organization.name] and 
                                existing_key[1] == doc.name):
                                doc_already_added = True
                                break
                    
                    if not doc_already_added:
                        try:
                            doc_data = doc.to_testpack()
                            export_data['objects']['documents'].append(doc_data)
                        except Exception:
                            pass
                    
                    # Add organization if not already present
                    org_already_added = False
                    for existing_org in export_data['objects']['organizations']:
                        if isinstance(existing_org, str):
                            # Parse the JSON string to check
                            try:
                                org_obj = json.loads(existing_org)
                                if org_obj.get('key', [None])[0] == doc.organization.name:
                                    org_already_added = True
                                    break
                            except:
                                pass
                        elif isinstance(existing_org, dict):
                            # Check if organization with same name already exists
                            existing_key = existing_org.get('key', [None])
                            if (isinstance(existing_key, list) and 
                                len(existing_key) >= 1 and
                                existing_key[0] == doc.organization.name):
                                org_already_added = True
                                break
                    
                    if not org_already_added:
                        try:
                            org_data = doc.organization.to_testpack()
                            export_data['objects']['organizations'].append(org_data)
                        except Exception:
                            pass
                    
                    # Get all requirements for this document
                    doc_reqs = Requirement.objects.filter(document=doc)
                    for req in doc_reqs:
                        try:
                            req_data = req.to_testpack()
                            export_data['objects']['requirements'].append(req_data)
                        except Exception as e:
                            logger.error(f"Failed to add requirement {req.tag_name}: {str(e)}")
                            pass
            
            # Create the download response
            response = HttpResponse(json.dumps(export_data, indent=2), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename={name}.accr'
            
            return response

        except Exception as e:
            raise


class ImportAccreditation(PermissionRequiredMixin, FormView):
    """View for importing accreditation data"""
    
    permission_required = 'accreditation.change_requirement'
    form_class = ImportAccreditationForm
    template_name = "admin/accreditation/import.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Import Accreditation Data")
        context['organizations'] = []
        context['documents'] = []
        context['requirements'] = []
        return context
    
    def get_success_url(self):
        """Redirect user to previous page they were on if possible"""
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_
        return reverse("admin:accreditation_document_changelist")
    
    def form_valid(self, form):
        """Handle the import form submission."""
        try:
            # Get the uploaded file content
            accreditation_file = form.cleaned_data['accreditation_file']
            accreditation_data = form.cleaned_data['accreditation_data']
            organizations = form.cleaned_data['organizations']
            documents = form.cleaned_data['documents']
            requirements = form.cleaned_data['requirements']
            
            # Parse the JSON data
            if not accreditation_data:
                # If no data in hidden field, read from file
                try:
                    file_content = accreditation_file.read().decode('utf-8')
                    accreditation_data = file_content
                except Exception as e:
                    messages.error(self.request, f"Error reading file: {str(e)}")
                    return self.form_invalid(form)
            
            # Parse the JSON data
            try:
                data = json.loads(accreditation_data)
            except json.JSONDecodeError as e:
                messages.error(self.request, f"Invalid JSON format: {str(e)}")
                return self.form_invalid(form)
            
            # Validate the data structure
            if not isinstance(data, dict) or 'objects' not in data or 'meta' not in data:
                messages.error(self.request, "Invalid accreditation file format")
                return self.form_invalid(form)
            
            # Parse selection parameters
            org_keys = None
            doc_keys = None
            req_keys = None
            
            if organizations and organizations != "all":
                try:
                    org_keys = json.loads(organizations)
                except ValueError:
                    org_keys = None
            
            if documents and documents != "all":
                try:
                    doc_keys = json.loads(documents)
                except ValueError:
                    doc_keys = None
            
            if requirements and requirements != "all":
                try:
                    req_keys = json.loads(requirements)
                except ValueError:
                    req_keys = None
            
            # Import the data
            with transaction.atomic():
                try:
                    counts, totals = self._import_accreditation_data(
                        data, 
                        self.request.user,
                        org_keys=org_keys,
                        doc_keys=doc_keys,
                        req_keys=req_keys
                    )
                    
                    # Build success message
                    count_msg = ", ".join(f"{counts[k]}/{totals[k]} {k}" for k in totals)
                    msg = _("Accreditation data imported successfully: %(item_counts)s were imported.") % {'item_counts': count_msg}
                    messages.success(self.request, msg)
                    
                    logger.info(f"User {self.request.user.username} imported accreditation data: {count_msg}")
                except Exception as e:
                    logger.exception(f"Error in _import_accreditation_data: {str(e)}")
                    raise
                
        except Exception as e:
            logger.exception("Error importing accreditation data")
            messages.error(self.request, _("Sorry, but an error occurred when trying to import your accreditation data. Please check the file format and try again."))
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def _import_accreditation_data(self, data, user, org_keys=None, doc_keys=None, req_keys=None):
        """
        Import accreditation data from the parsed JSON data.
        
        Args:
            data: Parsed JSON data from the accreditation file
            user: User performing the import
            org_keys: List of organization keys to import (None for all)
            doc_keys: List of document keys to import (None for all)
            req_keys: List of requirement keys to import (None for all)
            
        Returns:
            Tuple of (counts, totals) where counts is what was imported and totals is what was available
        """
        from .models import Organization, Document, Requirement
        
        logger.info(f"Starting import with org_keys: {org_keys}, doc_keys: {doc_keys}, req_keys: {req_keys}")
        logger.info(f"Data structure: {list(data['objects'].keys())}")
        
        # Debug: Log sample data structures
        if data['objects'].get('organizations'):
            sample_org = data['objects']['organizations'][0]
            if isinstance(sample_org, str):
                sample_org = json.loads(sample_org)
            logger.info(f"Sample organization structure: {sample_org}")
        
        if data['objects'].get('documents'):
            sample_doc = data['objects']['documents'][0]
            if isinstance(sample_doc, str):
                sample_doc = json.loads(sample_doc)
            logger.info(f"Sample document structure: {sample_doc}")
        
        if data['objects'].get('requirements'):
            sample_req = data['objects']['requirements'][0]
            if isinstance(sample_req, str):
                sample_req = json.loads(sample_req)
            logger.info(f"Sample requirement structure: {sample_req}")
            logger.info(f"Total requirements in data: {len(data['objects']['requirements'])}")
        else:
            logger.warning("No requirements found in data!")
        
        created = timezone.now()
        counts = Counter()
        totals = Counter()
        
        # Parse all the JSON strings and collect data
        organizations_data = []
        documents_data = []
        requirements_data = []
        
        # Process organizations
        for org_data in data['objects'].get('organizations', []):
            if isinstance(org_data, str):
                org_data = json.loads(org_data)
            
            totals['organizations'] += 1
            org_key = org_data.get('key', [])
            
            # Check if this organization should be imported
            if org_keys is None or tuple(org_key) in org_keys:
                organizations_data.append(org_data)
                counts['organizations'] += 1
        
        # Process documents
        for doc_data in data['objects'].get('documents', []):
            if isinstance(doc_data, str):
                doc_data = json.loads(doc_data)
            
            totals['documents'] += 1
            doc_key = doc_data.get('key', [])
            
            # Check if this document should be imported
            if doc_keys is None or tuple(doc_key) in doc_keys:
                documents_data.append(doc_data)
                counts['documents'] += 1
        
        # Process requirements
        logger.info(f"Processing {len(data['objects'].get('requirements', []))} requirements from data")
        for req_data in data['objects'].get('requirements', []):
            if isinstance(req_data, str):
                req_data = json.loads(req_data)
            
            totals['requirements'] += 1
            req_key = req_data.get('key', [])
            logger.info(f"Processing requirement with key: {req_key}")
            
            # Check if this requirement should be imported
            include_req = False
            if req_keys is None:
                include_req = True
                logger.info(f"Requirement {req_key} included (no specific selection)")
            else:
                include_req = tuple(req_key) in req_keys
                logger.info(f"Requirement {req_key} directly selected: {include_req}")
            
            # If not directly selected, check if it belongs to a selected document
            if not include_req and doc_keys is not None:
                doc_key = req_data['object']['fields'].get('document')
                logger.info(f"Checking if requirement belongs to selected document: {doc_key}")
                for doc_data in data['objects'].get('documents', []):
                    if isinstance(doc_data, str):
                        doc_data = json.loads(doc_data)
                    if doc_data.get('key') == doc_key:
                        include_req = tuple(doc_key) in doc_keys
                        logger.info(f"Document {doc_key} found, requirement included: {include_req}")
                        break
            
            if include_req:
                requirements_data.append(req_data)
                counts['requirements'] += 1
                logger.info(f"Requirement {req_key} added to import list")
            else:
                logger.info(f"Requirement {req_key} NOT included in import")
        
        logger.info(f"Processing {len(organizations_data)} organizations, {len(documents_data)} documents, {len(requirements_data)} requirements")
        
        # Create objects in dependency order
        extra_kwargs = {'created': created, 'created_by': user, 'modified': created, 'modified_by': user}
        
        # Step 1: Create organizations
        org_created = {}
        for org_data in organizations_data:
            try:
                fields = org_data['object']['fields'].copy()
                fields.update(extra_kwargs)
                
                # Handle natural key conflicts
                org_name = fields['name']
                counter = 1
                while Organization.objects.filter(name=org_name).exists():
                    org_name = f"{fields['name']}-{counter}"
                    counter += 1
                fields['name'] = org_name
                
                org = Organization.objects.create(**fields)
                org_created[tuple(org_data['key'])] = org
                logger.info(f"Created organization: {org.name}")
                
            except Exception as e:
                logger.error(f"Error creating organization {org_data.get('key', 'unknown')}: {str(e)}")
                continue
        
        # Step 2: Create documents
        doc_created = {}
        for doc_data in documents_data:
            try:
                fields = doc_data['object']['fields'].copy()
                fields.update(extra_kwargs)
                
                # Handle natural key conflicts
                doc_name = fields['name']
                org_key = fields['organization']
                
                # Extract organization name from nested structure
                if isinstance(org_key[0], (list, tuple)):
                    org_name = org_key[0][0]
                else:
                    org_name = org_key[0]
                
                counter = 1
                while Document.objects.filter(name=doc_name, organization__name=org_name).exists():
                    doc_name = f"{fields['name']}-{counter}"
                    counter += 1
                fields['name'] = doc_name
                
                # Set organization foreign key
                org_found = None
                for created_org_key, created_org in org_created.items():
                    if created_org_key[0] == org_name:
                        org_found = created_org
                        break
                
                if org_found:
                    fields['organization'] = org_found
                    logger.info(f"Using newly created organization: {org_found.name}")
                else:
                    # Try to find existing organization
                    try:
                        org_obj = Organization.objects.get(name=org_name)
                        fields['organization'] = org_obj
                        logger.info(f"Found existing organization: {org_obj.name}")
                    except Organization.DoesNotExist:
                        logger.warning(f"Organization {org_name} not found, skipping document {doc_name}")
                        continue
                
                doc = Document.objects.create(**fields)
                # Convert nested list to tuple for hashing
                doc_key_tuple = tuple(tuple(item) if isinstance(item, list) else item for item in doc_data['key'])
                doc_created[doc_key_tuple] = doc
                logger.info(f"Created document: {doc.name}")
                
            except Exception as e:
                logger.error(f"Error creating document {doc_data.get('key', 'unknown')}: {str(e)}")
                continue
        
        # Step 3: Create requirements
        for req_data in requirements_data:
            try:
                fields = req_data['object']['fields'].copy()
                fields.update(extra_kwargs)
                
                # Extract document info from nested structure
                doc_key = fields['document']
                
                # Parse the nested structure: [[['Test Org'], 'Test Doc'], 'Test Req']
                org_name, doc_name = self._extract_document_info(doc_key)
                
                # Handle natural key conflicts
                req_tag = fields['tag_name']
                counter = 1
                while Requirement.objects.filter(tag_name=req_tag, document__name=doc_name).exists():
                    req_tag = f"{fields['tag_name']}-{counter}"
                    counter += 1
                fields['tag_name'] = req_tag
                
                # Find the document
                doc_found = self._find_document(org_name, doc_name, doc_created)
                if doc_found:
                    fields['document'] = doc_found
                else:
                    logger.warning(f"Document {doc_name} not found, skipping requirement {req_tag}")
                    continue
                
                req = Requirement.objects.create(**fields)
                logger.info(f"Created requirement: {req.tag_name}")
                
            except Exception as e:
                logger.error(f"Error creating requirement {req_data.get('key', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"Import completed successfully: {len(org_created)} organizations, {len(doc_created)} documents created")
        return counts, totals
    
    def _extract_document_info(self, doc_key):
        """
        Extract organization and document names from the nested key structure.
        
        Args:
            doc_key: Document key from requirement data
            
        Returns:
            tuple: (org_name, doc_name)
        """
        # Structure: [[['Test Org'], 'Test Doc'], 'Test Req']
        # We need to extract org_name and doc_name from the document part
        if isinstance(doc_key[0], (list, tuple)) and len(doc_key[0]) >= 2:
            if isinstance(doc_key[0][0], (list, tuple)) and len(doc_key[0][0]) >= 1:
                # Structure: [[['Test Org'], 'Test Doc'], 'Test Req']
                org_name = doc_key[0][0][0]  # 'Test Org'
                doc_name = doc_key[0][1]     # 'Test Doc'
            else:
                # Fallback structure
                org_name = doc_key[0][0]     # 'Test Org'
                doc_name = doc_key[0][1]     # 'Test Doc'
        else:
            # Fallback: assume direct structure
            org_name = doc_key[0] if len(doc_key) > 0 else None
            doc_name = doc_key[1] if len(doc_key) > 1 else None
        
        return org_name, doc_name
    
    def _find_organization(self, org_name, org_created):
        """
        Find an organization in the newly created ones or existing database.
        
        Args:
            org_name: Name of the organization to find
            org_created: Mapping of created organization keys to objects
            
        Returns:
            Organization: Found organization object or None
        """
        # Look in newly created organizations
        for created_org_key, created_org in org_created.items():
            if created_org_key[0] == org_name:
                return created_org
        
        # Look in existing database
        try:
            return Organization.objects.get(name=org_name)
        except Organization.DoesNotExist:
            return None
    
    def _find_document(self, org_name, doc_name, doc_created):
        """
        Find a document in the newly created ones or existing database.
        
        Args:
            org_name: Name of the organization
            doc_name: Name of the document
            doc_created: Mapping of created document keys to objects
            
        Returns:
            Document: Found document object or None
        """
        # Look in newly created documents
        for created_doc_key, created_doc in doc_created.items():
            # created_doc_key structure: (('org_name',), 'doc_name')
            if (isinstance(created_doc_key[0], (list, tuple)) and 
                len(created_doc_key[0]) >= 1 and
                created_doc_key[0][0] == org_name and 
                created_doc_key[1] == doc_name):
                return created_doc
        
        # Look in existing database
        try:
            return Document.objects.get(name=doc_name, organization__name=org_name)
        except Document.DoesNotExist:
            return None
