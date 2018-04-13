
from django.conf import settings
from django.contrib import admin
from django.forms import ModelForm, ValidationError

from .models import ServiceEventStatus, ServiceType, UnitServiceArea, ServiceArea, ThirdParty, GroupLinker


class ServiceEventStatusFormAdmin(ModelForm):

    class Meta:
        model = ServiceEventStatus
        fields = '__all__'

    def clean_is_default(self):

        is_default = self.cleaned_data['is_default']
        if not is_default and self.initial.get('is_default', False):
            raise ValidationError('There must be one default status. Edit another status to be default first.')
        return is_default


class DeleteOnlyFromOwnFormAdmin(admin.ModelAdmin):

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return super(DeleteOnlyFromOwnFormAdmin, self).has_delete_permission(request, obj)


class ServiceEventStatusAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name', 'is_review_required', 'is_default', 'rts_qa_must_be_reviewed']
    form = ServiceEventStatusFormAdmin

    class Media:
        js = (
            settings.STATIC_URL + "jquery/js/jquery.min.js",
            settings.STATIC_URL + "colorpicker/js/bootstrap-colorpicker.min.js",
            settings.STATIC_URL + "qatrack_core/js/admin_colourpicker.js",

        )
        css = {
            'all': (
                settings.STATIC_URL + "bootstrap/css/bootstrap.min.css",
                settings.STATIC_URL + "colorpicker/css/bootstrap-colorpicker.min.css",
                settings.STATIC_URL + "qatrack_core/css/admin.css",
            ),
        }

    def delete_view(self, request, object_id, extra_context=None):

        if ServiceEventStatus.objects.get(pk=object_id).is_default:
            extra_context = extra_context or {'is_default': True}

        return super().delete_view(request, object_id, extra_context)


class ServiceTypeAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name', 'is_review_required', 'is_active']


class ServiceAreaAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name']
    filter_horizontal = ("units",)


if settings.USE_SERVICE_LOG:
    admin.site.register(ServiceArea, ServiceAreaAdmin)
    admin.site.register(ServiceType, ServiceTypeAdmin)
    admin.site.register(ServiceEventStatus, ServiceEventStatusAdmin)

    admin.site.register([ThirdParty, GroupLinker, UnitServiceArea], admin.ModelAdmin)
