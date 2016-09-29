
from django.contrib import admin
from models import ServiceEventStatus, ServiceType, ProblemType, UnitServiceArea, ServiceArea, ServiceEvent


class ServiceEventStatusAdmin(admin.ModelAdmin):
    list_display = ["name", "is_review_required", "is_default", "is_active"]


class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_approval_required', 'is_active']


class ProblemTypeAdmin(admin.ModelAdmin):
    list_display = ['name']


class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ['name']
    filter_horizontal = ("units",)


# class UnitServiceAreaAdmin(admin.ModelAdmin):
#     list_display = ['unit', 'service_area']


class ServiceEventAdmin(admin.ModelAdmin):
    list_display = ['unit_name', 'service_area_name']

    def unit_name(self, obj):
        return obj.unit_service_area_collection.unit

    def service_area_name(self, obj):
        return obj.unit_service_area_collection.service_area


class MembershipInline(admin.TabularInline):
    model = UnitServiceArea
    extra = 1


admin.site.register(ServiceEvent, ServiceEventAdmin)
# admin.site.register(UnitServiceArea, UnitServiceAreaAdmin)
admin.site.register(ServiceArea, ServiceAreaAdmin)
admin.site.register(ProblemType, ProblemTypeAdmin)
admin.site.register(ServiceType, ServiceTypeAdmin)
admin.site.register(ServiceEventStatus, ServiceEventStatusAdmin)
