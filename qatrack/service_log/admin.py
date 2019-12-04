from django.conf import settings
from django.contrib import admin
from django.db.models import Count, Max
from django.forms import ModelForm, ValidationError

from .models import (
    GroupLinker,
    ServiceArea,
    ServiceEvent,
    ServiceEventStatus,
    ServiceType,
    ThirdParty,
    UnitServiceArea,
)


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


class ServiceEventAdmin(DeleteOnlyFromOwnFormAdmin):

    list_display = [
        "get_se_id",
        "unit_service_area",
        "service_type",
        "service_status",
        "datetime_created",
        "datetime_modified",
        "is_review_required",
        "is_active",
    ]

    list_filter = ["unit_service_area", "service_type", "is_review_required", "is_active"]

    raw_id_fields = [
        "test_list_instance_initiated_by",
    ]

    filter_horizontal = ["service_event_related"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "unit_service_area":
            kwargs['queryset'] = UnitServiceArea.objects.select_related("unit", "service_area")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_se_id(self, obj):
        return "Service Event #%d" % obj.pk

    def get_queryset(self, request):

        qs = self.model.all_objects.get_queryset()

        # we need this from the superclass method
        ordering = self.ordering or () # otherwise we might try to *None, which is bad ;)
        if ordering:
            qs = qs.order_by(*ordering)

        qs = qs.select_related(
            "unit_service_area",
            "unit_service_area__service_area",
            "unit_service_area__unit",
        )
        return qs


class ServiceEventStatusAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name', 'is_review_required', 'is_default', 'rts_qa_must_be_reviewed', 'order']
    list_editable = ['order']
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


class UnitServiceAreaAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['__str__', 'notes']
    list_filter = ['unit', 'service_area']
    search_fields = ['unit__name', 'service_area__name']


class GroupLinkerAdminForm(ModelForm):

    class Meta:
        model = GroupLinker
        fields = '__all__'

    def clean_multiple(self):
        # check if this group linker has cases where there are already multiple group linker instances
        # pointing to it, and if so, don't allow disabling of multiple
        multiple = self.cleaned_data.get("multiple")
        if self.instance and not multiple:
            max_counts = self.instance.grouplinkerinstance_set.values(
                "service_event_id",
            ).annotate(
                counts=Count("service_event_id"),
            ).order_by(
                "counts",
            ).aggregate(max_counts=Max("counts"))['max_counts']
            if max_counts and max_counts > 1:
                raise ValidationError(
                    'You can not disable "multiple" for since there are Service Events'
                    'with multiple Group Linker Instances referring to this Group Linker'
                )
        return multiple


class GroupLinkerAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name', 'group', 'required', 'multiple', 'description', 'help_text']
    list_filter = ['group']
    search_fields = ['name', 'group__name']

    form = GroupLinkerAdminForm


if settings.USE_SERVICE_LOG:
    admin.site.register(ServiceArea, ServiceAreaAdmin)
    admin.site.register(ServiceEvent, ServiceEventAdmin)
    admin.site.register(ServiceType, ServiceTypeAdmin)
    admin.site.register(ServiceEventStatus, ServiceEventStatusAdmin)
    admin.site.register(UnitServiceArea, UnitServiceAreaAdmin)
    admin.site.register(GroupLinker, GroupLinkerAdmin)

    admin.site.register([ThirdParty], admin.ModelAdmin)
