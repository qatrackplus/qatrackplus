from django import forms
from django.contrib import admin
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.notifications import models
from qatrack.qatrack_core.admin import BaseQATrackAdmin


class ServiceEventSchedulingNoticeAdminForm(forms.ModelForm):
    """Form for handling validation of ServiceEventSchedulingNotice creation/editing"""

    class Meta:
        model = models.ServiceEventSchedulingNotice
        fields = (
            "notification_type",
            "send_empty",
            "recurrences",
            "time",
            "future_days",
            "recipients",
            "units",
        )

    def get_queryset(self, request):  # pragma: nocover
        return super().get_queryset(request).prefetch_related(
            "recipients__users",
            "recipients__groups",
            "units__units",
        )

    def clean(self):

        cleaned_data = super().clean()

        nt = cleaned_data['notification_type']
        future_days = cleaned_data.get('future_days')
        if nt in [models.ServiceEventSchedulingNotice.UPCOMING, models.ServiceEventSchedulingNotice.UPCOMING_AND_DUE]:
            if future_days in ("", None):
                msg = _("You must set the number of days in future to include for upcoming QC due date notices")
                self.add_error("future_days", forms.ValidationError(msg))
        elif future_days not in ("", None):
            msg = _("Leave 'Future days' blank if not creating an Upcoming QC notification")
            self.add_error("future_days", forms.ValidationError(msg))

        return cleaned_data


class ServiceEventSchedulingAdmin(BaseQATrackAdmin):

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

    form = ServiceEventSchedulingNoticeAdminForm

    fieldsets = (
        (None, {
            'fields': ["notification_type", "send_empty", "recurrences", "time", "future_days"],
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
            "admin/js/jquery.init.js",
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
            "units__units",
        )

    def get_notification_type(self, obj):
        disp = "#%s - %s" % (obj.pk, obj.get_notification_type_display())
        ntypes = [models.ServiceEventSchedulingNotice.UPCOMING, models.ServiceEventSchedulingNotice.UPCOMING_AND_DUE]
        if obj.notification_type in ntypes:
            disp = disp + _(" (next %(num_days)s days)") % {'num_days': obj.future_days}
        return disp

    def get_units(self, obj):
        return obj.units.name if obj.units else ""
    get_units.admin_order_field = "units__name"
    get_units.short_description = _l("Units Group")

    def get_recipients(self, obj):
        return obj.recipients.name
    get_recipients.admin_order_field = "recipients__name"
    get_recipients.short_description = _l("Recipient Group")


admin.site.register([models.ServiceEventSchedulingNotice], ServiceEventSchedulingAdmin)
