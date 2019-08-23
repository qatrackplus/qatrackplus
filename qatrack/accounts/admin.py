from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _l


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
        if obj:
            form.base_fields['is_staff'].label = _("Admin Status")

        return form

    def is_admin(self, obj):
        return obj.is_staff
    is_admin.boolean = True


admin.site.unregister(User)
admin.site.register(User, QATrackUserAdmin)
