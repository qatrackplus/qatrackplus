from django import forms
from django.conf import settings
from django.contrib import admin
from django.template.defaultfilters import truncatechars
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _l

from qatrack.notifications import models


def trim(string, length=200):
    return truncatechars(string, length)


class QCCompletedNoticeAdminForm(forms.ModelForm):
    """Form for handling validation of QCCompletedNotice creation/editing"""

    class Meta:
        model = models.QCCompletedNotice
        fields = (
            "notification_type",
            "follow_up_days",
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

        is_follow_up = cleaned_data['notification_type'] == models.QCCompletedNotice.FOLLOW_UP
        if is_follow_up and cleaned_data.get('follow_up_days') in ("", None):
            msg = _("You must set the number of days to follow after for Follow Up notifications.")
            self.add_error("follow_up_days", forms.ValidationError(msg))
        elif cleaned_data.get("follow_up_days") not in ("", None):
            msg = _("Leave 'Follow up days' blank if not creating a Follow Up notification")
            self.add_error("follow_up_days", forms.ValidationError(msg))

        return cleaned_data


class QCCompletedAdmin(admin.ModelAdmin):

    list_display = ["get_notification_type", "get_recipients", "get_testlists", "get_units"]
    list_filter = ["notification_type", "recipients", "test_lists", "units"]
    search_fields = [
        "units__units__number",
        "units__units__name",
        "recipients__groups__name",
        "recipients__users__name",
        "recipients__users__email",
        "recipients__groups__user__email",
        "test_lists__test_lists__name",
    ]

    form = QCCompletedNoticeAdminForm

    fieldsets = (
        (None, {
            'fields': ["notification_type", "follow_up_days"],
        }),
        (
            "Recipients", {
                'fields': ["recipients"],
                'description': _("Select which recipient group should receive this notification."),
            }
        ),
        (
            "Filters", {
                'fields': ['units', 'test_lists'],
                'description':
                    _("By using the below filters, you may limit this notification to "
                      "certain units or test lists."),
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
        if obj.notification_type == models.QCCompletedNotice.FOLLOW_UP:
            return _("Follow up notification (after %(num_days)s days)") % {'num_days': obj.follow_up_days}
        return obj.get_notification_type_display()

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


admin.site.register([models.QCCompletedNotice], QCCompletedAdmin)
