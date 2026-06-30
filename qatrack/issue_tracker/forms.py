from qatrack.issue_tracker import models
from qatrack.qatrack_core.forms import BetterModelForm


class IssueForm(BetterModelForm):

    class Meta:
        model = models.Issue
        fields = ['issue_type', 'issue_priority', 'issue_tags', 'description', 'error_screen']
        fieldsets = [
            ('hidden_fields', {
                'fields': [],
            }),
            ('required_fields', {
                'fields': ['issue_type', 'issue_priority', 'issue_tags', 'description', 'error_screen'],
            }),
            ('optional_fields', {
                'fields': []
            })
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
