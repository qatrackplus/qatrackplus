from django.conf import settings
from django.contrib import admin
from qatrack.issue_tracker import models as i_models


class IssueAdmin(admin.ModelAdmin):
    list_display = ['id', 'issue_status', 'issue_priority', 'issue_type', 'description']
    search_fields = ['description']


class IssueTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['description']


class IssueTagAdmin(admin.ModelAdmin):

    list_display = ['id', 'name', 'description']


class IssuePriorityStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'colour', 'order']

    class Media:
        js = (
            settings.STATIC_URL + 'jquery/js/jquery.min.js',
            settings.STATIC_URL + 'colorpicker/js/bootstrap-colorpicker.min.js',
            settings.STATIC_URL + 'qatrack_core/js/admin_colourpicker.js',

        )
        css = {
            'all': (
                settings.STATIC_URL + 'bootstrap/css/bootstrap.min.css',
                settings.STATIC_URL + 'colorpicker/css/bootstrap-colorpicker.min.css',
                settings.STATIC_URL + 'qatrack_core/css/admin.css',
            ),
        }

if settings.USE_ISSUES:

    admin.site.register([i_models.IssueType], IssueTypeAdmin)
    admin.site.register([i_models.IssuePriority, i_models.IssueStatus], IssuePriorityStatusAdmin)
    admin.site.register([i_models.Issue], IssueAdmin)
    admin.site.register([i_models.IssueTag], IssueTagAdmin)
