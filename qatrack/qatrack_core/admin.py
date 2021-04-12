from django.contrib import admin
from django.utils import timezone


class SaveUserMixin:
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


class DisableInlineEditMixin:
    """A mixin to disable the inline edit/delete links for foreign key choices in the admin"""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield and formfield.widget and hasattr(formfield.widget, 'can_delete_related'):
            formfield.widget.can_delete_related = False
            formfield.widget.can_change_related = False
        return formfield


class BaseQATrackAdmin(DisableInlineEditMixin, admin.ModelAdmin):
    pass


class SaveUserQATrackAdmin(SaveUserMixin, BaseQATrackAdmin):
    """Adds SaveUser functionality to the BaseQATrackAdmin"""
