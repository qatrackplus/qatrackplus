from django import forms
from django.conf import settings
from django.contrib import admin
from django.template.defaultfilters import truncatechars
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _l

from qatrack.notifications import models
from qatrack.units.forms import unit_site_unit_type_choices


class NotificationAdminForm(forms.ModelForm):
    """Form for handling validation of NotificationSubscription creation/editing"""

    class Meta:
        model = models.NotificationSubscription
        fields = (
            "notification_type",
            "follow_up_days",
            "groups",
            "users",
            "units",
            "test_lists",
        )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['units'].choices = unit_site_unit_type_choices()

    def get_queryset(self, request):  # pragma: nocover
        return super().get_queryset(request).prefetch_related(
            "users",
            "groups",
            "test_lists",
            "units",
        )

    def clean(self):
        cleaned_data = super().clean()
        no_groups = len(cleaned_data.get('groups', [])) == 0
        no_users = len(cleaned_data.get('users', [])) == 0
        if no_groups and no_users:
            msg = _("You must select at least one group or user!")
            self.add_error(None, forms.ValidationError(msg))

        no_tls = len(cleaned_data.get('test_lists', [])) == 0
        if cleaned_data['notification_type'] == models.FOLLOW_UP:
            if no_tls:
                msg = _("You must select at least one Test List for Follow Up notifications.")
                self.add_error(None, forms.ValidationError(msg))

            if cleaned_data.get('follow_up_days') in ("", None):
                msg = _("You must set the number of days to follow after for Follow Up notifications.")
                self.add_error("follow_up_days", forms.ValidationError(msg))
        elif cleaned_data.get("follow_up_days") not in ("", None):
            msg = _("Leave 'Follow up days' blank if not creating a Follow Up notification")
            self.add_error("follow_up_days", forms.ValidationError(msg))

        return cleaned_data


class NotificationAdmin(admin.ModelAdmin):

    list_display = ["get_notification_type", "get_units", "get_groups", "get_users", "get_testlists"]
    list_filter = ["notification_type", "units", "groups"]
    search_fields = [
        "units__number",
        "units__name",
        "groups__name",
        "users__name",
        "users__email",
        "groups__user__email",
        "test_lists__name",
    ]

    form = NotificationAdminForm

    fieldsets = (
        (None, {
            'fields': ["notification_type", "follow_up_days"],
        }),
        (
            "Recipients", {
                'fields': ["users", "groups"],
                'description': _("Select which groups and/or users should receive this notification type"),
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
        qs = super().get_queryset(request).prefetch_related("units", "groups", "users")
        return qs

    def get_notification_type(self, obj):
        if obj.notification_type == models.FOLLOW_UP:
            return _("Follow up notification (after %(num_days)s days)") % {'num_days': obj.follow_up_days}
        return obj.get_notification_type_display()

    def get_units(self, obj):
        return self.trim(', '.join(obj.units.values_list("name", flat=True)))
    get_units.admin_order_field = "units__name"
    get_units.short_description = _l("Units")

    def get_groups(self, obj):
        return self.trim(', '.join(obj.groups.values_list("name", flat=True)))
    get_groups.admin_order_field = "groups__name"
    get_groups.short_description = _l("Groups")

    def get_users(self, obj):
        return self.trim(', '.join("%s (%s)" % (u.username, u.email) for u in obj.users.all()))
    get_users.admin_order_field = "users__username"
    get_users.short_description = _l("Users")

    def get_testlists(self, obj):
        return ', '.join(obj.test_lists.values_list("name", flat=True))
    get_testlists.admin_order_field = "test_lists__name"
    get_testlists.short_description = _l("Test Lists")

    def trim(self, string):
        return truncatechars(string, 200)


admin.site.register([models.NotificationSubscription], NotificationAdmin)
