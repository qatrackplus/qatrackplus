from django.contrib import admin
from django.utils import timezone


class SaveUserMixin(object):
    """A Mixin to save creating user and modifiying user

    Set editable=False on the created_by and modified_by model you
    want to use this for.
    """

    def save_model(self, request, obj, form, change):
        """set user and modified date time"""
        if not obj.pk:
            obj.created_by = request.user
            obj.created = timezone.now()
        obj.modified_by = request.user

        super(SaveUserMixin, self).save_model(request, obj, form, change)


class BasicSaveUserAdmin(SaveUserMixin, admin.ModelAdmin):
    """manage reference values for tests"""
