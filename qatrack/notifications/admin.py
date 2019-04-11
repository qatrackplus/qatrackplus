from itertools import groupby

from django import forms
from django.contrib import admin
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _l

from qatrack.units.models import Unit

from . import models


class NotificationAdminForm(forms.ModelForm):
    """Form for handling validation of TestList creation/editing"""

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        def site_unit_type(u):
            return "%s :: %s" % (u.site.name if u.site else "Other", u.type.name)

        def site_unit_name(u):
            return "%s :: %s" % (u.site.name if u.site else "Other", u.name)

        units = Unit.objects.select_related("site", "type").order_by("site__name", "type__name", "name")
        choices = [(ut, list(us)) for (ut, us) in groupby(units, key=site_unit_type)]
        choices = [(ut, [(u.id, site_unit_name(u)) for u in us]) for (ut, us) in choices]
        choices = [("", "---------")] + choices

        import ipdb; ipdb.set_trace()  # yapf: disable  # noqa
        self.fields['units'].choices = choices

    def clean(self):
        cleaned_data = super().clean()
        no_groups = len(cleaned_data.get('groups', [])) == 0
        no_users = len(cleaned_data.get('users', [])) == 0
        if no_groups and no_users:
            msg = _("You must select at least one group or user!")
            self.add_error(None, forms.ValidationError(msg))

        return cleaned_data


class NotificationAdmin(admin.ModelAdmin):

    list_display = ["warning_level", "get_units", "get_groups", "get_users"]
    list_filter = ["warning_level", "units", "groups"]
    search_fields = [
        "units__number",
        "units__name",
        "groups__name",
        "users__name",
        "users__email",
        "groups__user__email",
    ]

    filter_horizontal = ("groups", "users", "units", )

    form = NotificationAdminForm

    def get_queryset(self, request):
        qs = super().get_queryset(request).prefetch_related("units", "groups", "users")
        return qs

    def get_units(self, obj):
        return ', '.join(u.name for u in obj.units.all())
    get_units.admin_order_field = "units__name"
    get_units.short_description = _l("Units")

    def get_groups(self, obj):
        return ', '.join(g.name for g in obj.groups.all())
    get_groups.admin_order_field = "groups__name"
    get_groups.short_description = _l("Groups")

    def get_users(self, obj):
        return ', '.join("%s (%s)" % (u.username, u.email) for u in obj.users.all())
    get_users.admin_order_field = "users__username"
    get_users.short_description = _l("Users")


admin.site.register([models.NotificationSubscription], NotificationAdmin)
