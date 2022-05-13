from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template.defaultfilters import truncatechars
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.notifications import models
from qatrack.qatrack_core.admin import BaseQATrackAdmin


def trim(string, length=200):
    return truncatechars(string, length)


class RecipientGroupForm(forms.ModelForm):

    class Meta:
        model = models.RecipientGroup
        fields = (
            "name",
            "groups",
            "users",
            "emails",
        )

    def clean_emails(self):
        emails = self.cleaned_data.get("emails", "")
        invalid_emails = []
        valid_emails = []
        for email in emails.strip().split(","):
            email = email.strip()
            if not email:
                continue
            try:
                validate_email(email)
                valid_emails.append(email)
            except ValidationError:
                invalid_emails.append(email)

        if invalid_emails:
            self.add_error("emails", "%s: %s" % (_("The following emails are invalid"), ", ".join(invalid_emails)))

        return ", ".join(sorted(invalid_emails + valid_emails))

    def clean(self):
        cleaned_data = super().clean()
        no_groups = len(cleaned_data.get('groups', [])) == 0
        no_users = len(cleaned_data.get('users', [])) == 0
        no_emails = len(cleaned_data.get('emails', "").strip()) == 0

        if no_groups and no_users and no_emails:
            msg = _("You must select at least one group, user, or email address!")
            self.add_error(None, forms.ValidationError(msg))

        return cleaned_data


class RecipientGroupAdmin(BaseQATrackAdmin):

    list_display = ["name", "get_users", "get_groups", "get_emails"]
    list_filter = ["groups", "users"]
    search_fields = [
        "groups__name",
        "users__username",
        "users__first_name",
        "users__last_name",
        "users__email",
        "groups__user__email",
        "groups__user__username",
        "groups__user__first_name",
        "groups__user__last_name",
    ]

    form = RecipientGroupForm

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

    def get_groups(self, obj):
        return trim(', '.join(obj.groups.values_list("name", flat=True)))

    get_groups.admin_order_field = "groups__name"
    get_groups.short_description = _l("Groups")

    def get_users(self, obj):
        return trim(', '.join("%s (%s)" % (u.username, u.email) for u in obj.users.all()))

    get_users.admin_order_field = "users__username"
    get_users.short_description = _l("Users")

    def get_emails(self, obj):
        return trim(obj.emails)

    get_emails.short_description = _l("Emails")
    get_users.admin_order_field = "emails"


class TestListGroupForm(forms.ModelForm):

    class Meta:
        model = models.TestListGroup
        fields = ("name", "test_lists")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['test_lists'].queryset = self.fields['test_lists'].queryset.order_by("name")


class TestListGroupAdmin(BaseQATrackAdmin):

    list_display = ["name", "get_test_lists"]
    list_filter = ["test_lists"]
    search_fields = [
        "test_lists__name",
        "test_lists__slug",
    ]

    form = TestListGroupForm

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

    def get_test_lists(self, obj):
        return trim(', '.join(obj.test_lists.values_list("name", flat=True)))

    get_test_lists.admin_order_field = "test_lists__name"
    get_test_lists.short_description = _l("Test Lists")


class UnitGroupAdmin(BaseQATrackAdmin):

    list_display = ["name", "get_units"]
    list_filter = ["units", "units__site"]
    search_fields = [
        "name",
        "units__name",
        "units__number",
    ]

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

    def get_units(self, obj):
        return trim(', '.join(obj.units.values_list("name", flat=True)))

    get_units.admin_order_field = "units__name"
    get_units.short_description = _l("Units")


admin.site.register([models.RecipientGroup], RecipientGroupAdmin)
admin.site.register([models.TestListGroup], TestListGroupAdmin)
admin.site.register([models.UnitGroup], UnitGroupAdmin)
