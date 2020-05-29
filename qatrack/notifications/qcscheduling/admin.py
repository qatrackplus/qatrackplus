from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.notifications import models
from qatrack.qatrack_core.admin import BaseQATrackAdmin


class QCSchedulingNoticeAdminForm(forms.ModelForm):
    """Form for handling validation of QCSchedulingNotice creation/editing"""

    class Meta:
        model = models.QCSchedulingNotice
        fields = (
            "notification_type",
            "send_empty",
            "recurrences",
            "time",
            "future_days",
            "recipients",
            "units",
            "test_lists",
        )

    def get_queryset(self, request):  # pragma: nocover
        return super().get_queryset(request).prefetch_related(
            "recipients__users",
            "recipients__groups",
            "test_lists__test_lists",
            "units__units",
        )

    def clean(self):

        cleaned_data = super().clean()

        nt = cleaned_data['notification_type']
        future_days = cleaned_data.get('future_days')
        if nt in [models.QCSchedulingNotice.UPCOMING, models.QCSchedulingNotice.UPCOMING_AND_DUE]:
            if future_days in ("", None):
                msg = _("You must set the number of days in future to include for upcoming QC due date notices")
                self.add_error("future_days", forms.ValidationError(msg))
        elif future_days not in ("", None):
            msg = _("Leave 'Future days' blank if not creating an Upcoming QC notification")
            self.add_error("future_days", forms.ValidationError(msg))

        return cleaned_data


class QCSchedulingAdmin(BaseQATrackAdmin):

    list_display = ["get_notification_type", "get_recipients", "get_testlists", "get_units", "send_empty"]
    list_filter = ["notification_type", "recipients", "test_lists", "units"]
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
        "test_lists__test_lists__name",
    ]

    form = QCSchedulingNoticeAdminForm

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
                'fields': ['units', 'test_lists'],
                'description': _l(
                    "By using the below filters, you may limit this notification to "
                    "certain units or test lists."
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
            "test_lists__test_lists",
            "units__units",
        )

    def get_notification_type(self, obj):
        disp = "#%s - %s" % (obj.pk, obj.get_notification_type_display())
        if obj.notification_type in [models.QCSchedulingNotice.UPCOMING, models.QCSchedulingNotice.UPCOMING_AND_DUE]:
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

    def get_testlists(self, obj):
        return obj.test_lists.name if obj.test_lists else ""
    get_testlists.admin_order_field = "test_lists__name"
    get_testlists.short_description = _l("TestList Group")


admin.site.register([models.QCSchedulingNotice], QCSchedulingAdmin)
