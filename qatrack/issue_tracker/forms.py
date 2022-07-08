from django import forms
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db.models import ObjectDoesNotExist, Q
from django.utils.encoding import force_text
from form_utils.forms import BetterModelForm

from qatrack.issue_tracker import models as i_models


class IssueForm(BetterModelForm):

    class Meta:
        model = i_models.Issue
        fieldsets = [('hidden_fields', {
            'fields': [],
        }),
                     (
                         'required_fields', {
                             'fields': ['issue_type', 'issue_priority', 'issue_tags', 'description', 'error_screen'],
                         }
                     ), ('optional_fields', {
                         'fields': []
                     })]

    def __init__(self, *args, **kwargs):
        super(IssueForm, self).__init__(*args, **kwargs)

        self.fields['issue_type'].label = 'Type'
        self.fields['issue_priority'].label = 'Priority'
        self.fields['issue_priority'].label = 'Priority'
        self.fields['error_screen'].label = 'Error Screen Details'
        # s = i_models.IssueTag.objects.get(pk=100)

        for f in self.fields:
            self.fields[f].widget.attrs['class'] = 'form-control'

        for f in ['description', 'error_screen']:
            self.fields[f].widget.attrs['class'] += ' autosize'
            self.fields[f].widget.attrs['rows'] = 8
            self.fields[f].widget.attrs['cols'] = 8
