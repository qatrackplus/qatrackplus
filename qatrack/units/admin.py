from django.contrib import admin
from models import Unit, Modality, UnitType


class UnitAdmin(admin.ModelAdmin):
    filter_horizontal = ("modalities",)

admin.site.register([Unit], UnitAdmin)
admin.site.register([Modality, UnitType])
