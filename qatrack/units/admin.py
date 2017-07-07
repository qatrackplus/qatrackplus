from django.contrib import admin
from .models import Modality, UnitType, Site, UnitClass, Vendor


# class UnitAdmin(admin.ModelAdmin):
#     filter_horizontal = ("modalities",)

class NoDeleteAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


# admin.site.register([Unit], UnitAdmin) # UnitAdmin registered in service_log\admin
admin.site.register([Modality, UnitType, Site, UnitClass, Vendor], NoDeleteAdmin)
