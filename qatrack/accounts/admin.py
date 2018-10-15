from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User


class QATrackUserAdmin(UserAdmin):

    def has_change_permission(self, request, obj=None):

        if obj and obj.username == "QATrack+ Internal":
           return False

        return super(QATrackUserAdmin, self).has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.unregister(User)
admin.site.register(User, QATrackUserAdmin)
