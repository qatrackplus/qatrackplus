from django.conf import settings
from django.contrib import admin

from qatrack.issue_tracker import models as i_models
from qatrack.qatrack_core.admin import BaseQATrackAdmin


class IssueAdmin(BaseQATrackAdmin):
    list_display = ['id', 'issue_status', 'issue_priority', 'issue_type', 'description']
    search_fields = ['description']


class IssueTypeAdmin(BaseQATrackAdmin):
    list_display = ['id', 'name']
    search_fields = ['description']


class IssueTagAdmin(BaseQATrackAdmin):

    list_display = ['id', 'name', 'description']


class IssuePriorityStatusAdmin(BaseQATrackAdmin):
    list_display = ['name', 'colour', 'order']

    class Media:
        js = (
            "admin/js/jquery.init.js",
            'jquery/js/jquery.min.js',
            'colorpicker/js/bootstrap-colorpicker.min.js',
            'qatrack_core/js/admin_colourpicker.js',
        )
        css = {
            'all': (
                'bootstrap/css/bootstrap.min.css',
                'colorpicker/css/bootstrap-colorpicker.min.css',
                'qatrack_core/css/admin.css',
            ),
        }


if settings.USE_ISSUES:

    admin.site.register([i_models.IssueType], IssueTypeAdmin)
    admin.site.register([i_models.IssuePriority, i_models.IssueStatus], IssuePriorityStatusAdmin)
    admin.site.register([i_models.Issue], IssueAdmin)
    admin.site.register([i_models.IssueTag], IssueTagAdmin)
