from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.accounts import models
from qatrack.qatrack_core.admin import BaseQATrackAdmin


class AdminFilter(admin.SimpleListFilter):
    # Replace Staff with Admin

    title = _l('Admin Status')

    parameter_name = 'is_admin'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    def queryset(self, request, queryset):

        if self.value() == 'yes':
            return queryset.filter(is_staff=True)

        elif self.value() == 'no':
            return queryset.filter(is_staff=False)

        return queryset


class QATrackUserAdmin(UserAdmin):

    list_filter = (AdminFilter, 'is_superuser', 'is_active', 'groups')
    list_display = ('username', 'email', 'first_name', 'last_name', "is_admin")

    def has_change_permission(self, request, obj=None):

        if obj and obj.username == "QATrack+ Internal":
            return False

        return super(QATrackUserAdmin, self).has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        if obj and 'is_staff' in form.base_fields:
            form.base_fields['is_staff'].label = _("Admin Status")

        return form

    def is_admin(self, obj):
        return obj.is_staff
    is_admin.boolean = True


class ActiveDirectoryGroupMapAdmin(BaseQATrackAdmin):

    list_display = ("get_ad_group", "get_groups", "account_qualifier")
    list_filter = ("groups", "account_qualifier",)
    search_fields = ("ad_group", "groups__name")

    def get_groups(self, obj):
        return ', '.join(sorted(obj.groups.values_list("name", flat=True)))

    get_groups.short_description = _l("QATrack+ Groups")

    @mark_safe
    def get_ad_group(self, obj):
        if not obj.ad_group:
            return '<em>' + _("Default Groups") + "</em>"
        return escape(obj.ad_group)
    get_ad_group.short_description = _l("Active Directory Group Name")


admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, QATrackUserAdmin)
admin.site.register(Group, BaseQATrackAdmin)
admin.site.register(models.ActiveDirectoryGroupMap, ActiveDirectoryGroupMapAdmin)
