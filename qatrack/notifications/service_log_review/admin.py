from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils.translation import gettext_lazy as _l

from qatrack.notifications import models
from qatrack.qatrack_core.admin import BaseQATrackAdmin


class ServiceEventReviewNoticeAdminForm(forms.ModelForm):
    """Form for handling validation of ServiceEventReviewNotice creation/editing"""

    class Meta:
        model = models.ServiceEventReviewNotice
        fields = (
            "notification_type",
            "send_empty",
            "recurrences",
            "time",
            "recipients",
            "units",
        )

    def get_queryset(self, request):  # pragma: nocover
        return super().get_queryset(request).prefetch_related(
            "recipients__users",
            "recipients__groups",
            "units__units",
        )


class ServiceEventReviewAdmin(BaseQATrackAdmin):

    list_display = ["get_notification_type", "get_recipients", "get_units", "send_empty"]
    list_filter = ["notification_type", "recipients", "units"]
    search_fields = [
        "units__units__number",
        "units__units__name",
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

    form = ServiceEventReviewNoticeAdminForm

    fieldsets = (
        (None, {
            'fields': ["notification_type", "send_empty", "recurrences", "time"],
        }),
        (
            "Recipients", {
                'fields': ["recipients"],
                'description': _l("Select which recipient group should receive this notification."),
            }
        ),
        (
            "Filters", {
                'fields': ['units'],
                'description': _l(
                    "By using the below filters, you may limit this notification to "
                    "certain units."
                ),
            }
        ),
    )

    class Media:
        js = (
            settings.STATIC_URL + "jquery/js/jquery.min.js",
            settings.STATIC_URL + "select2/js/select2.js",
            settings.STATIC_URL + "js/notification_admin.js",
        )
        css = {
            'all': (
                settings.STATIC_URL + "select2/css/select2.css",
            ),
        }

    def get_queryset(self, request):  # pragma: nocover
        return super().get_queryset(request).prefetch_related(
            "recipients__users",
            "recipients__groups",
            "units__units",
        )

    def get_notification_type(self, obj):
        disp = "#%s - %s" % (obj.pk, obj.get_notification_type_display())
        return disp

    def get_units(self, obj):
        return obj.units.name if obj.units else ""
    get_units.admin_order_field = "units__name"
    get_units.short_description = _l("Units Group")

    def get_recipients(self, obj):
        return obj.recipients.name
    get_recipients.admin_order_field = "recipients__name"
    get_recipients.short_description = _l("Recipient Group")


admin.site.register([models.ServiceEventReviewNotice], ServiceEventReviewAdmin)
