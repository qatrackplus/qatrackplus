from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _l

from qatrack.notifications.common.admin import trim
from qatrack.notifications.parts import models
from qatrack.qatrack_core.admin import BaseQATrackAdmin


class PartNoticeAdminForm(forms.ModelForm):
    """Form for handling validation of PartNotice creation/editing"""

    class Meta:
        model = models.PartNotice
        fields = (
            "notification_type",
            "recipients",
            "part_categories",
        )

    def get_queryset(self, request):  # pragma: nocover
        return super().get_queryset(request).prefetch_related(
            "recipients__users",
            "recipients__groups",
            "part_categories__part_categories",
        )


class PartNoticeAdmin(BaseQATrackAdmin):

    list_display = ["get_notification_type", "get_recipients", "get_categories"]
    list_filter = ["notification_type", "recipients", "part_categories"]
    search_fields = [
        "part_categories__part_categories__name",
        "recipients__groups__name",
        "recipients__users__username",
        "recipients__users__first_name",
        "recipients__users__last_name",
        "recipients__users__email",
        "recipients__groups__user__email",
        "recipients__groups__user__username",
        "recipients__groups__user__first_name",
        "recipients__groups__user__last_name",
    ]

    form = PartNoticeAdminForm

    fieldsets = (
        (None, {
            'fields': ["notification_type"],
        }),
        (
            "Recipients", {
                'fields': ["recipients"],
                'description': _l("Select which recipient group should receive this notification."),
            }
        ),
        (
            "Filters", {
                'fields': ['part_categories'],
                'description':
                    _l("By using the below filters, you may limit this notification to certain part categories."),
            }
        ),
    )

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'jquery/js/jquery.min.js',
            "select2/js/select2.js",
            "js/notification_admin.js",
        )
        css = {
            'all': ("select2/css/select2.css",),
        }

    def get_queryset(self, request):  # pragma: nocover
        return super().get_queryset(request).prefetch_related(
            "recipients__users",
            "recipients__groups",
            "part_categories__part_categories",
        )

    def get_notification_type(self, obj):
        return "#%s - %s" % (obj.pk, obj.get_notification_type_display())

    @admin.display(
        description=_l("Part Categories Group"),
        ordering="part_categories__name",
    )
    def get_categories(self, obj):
        return obj.part_categories.name if obj.part_categories else ""

    @admin.display(
        description=_l("Recipient Group"),
        ordering="recipients__name",
    )
    def get_recipients(self, obj):
        return obj.recipients.name


class PartCategoryGroupAdmin(BaseQATrackAdmin):

    list_display = ["name", "get_categories"]
    list_filter = ["part_categories"]
    search_fields = [
        "name",
        "part_categories__name",
    ]

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'jquery/js/jquery.min.js',
            "select2/js/select2.js",
            "js/notification_admin.js",
        )
        css = {
            'all': ("select2/css/select2.css",),
        }

    @admin.display(
        description=_l("Part Categories"),
        ordering="part_categories__name",
    )
    def get_categories(self, obj):
        return trim(', '.join(obj.part_categories.values_list("name", flat=True)))


admin.site.register([models.PartNotice], PartNoticeAdmin)
admin.site.register([models.PartCategoryGroup], PartCategoryGroupAdmin)
