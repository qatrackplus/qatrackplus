from django.contrib import admin
from django.utils.translation import gettext_lazy as _l

from qatrack.faults import models
from qatrack.qa.admin import SiteFilter, site_name
from qatrack.qatrack_core.admin import BaseQATrackAdmin, SaveUserQATrackAdmin
from qatrack.units.models import Modality


class FaultTypeAdmin(BaseQATrackAdmin):

    list_display = ("code", "description")
    search_fields = (
        "name",
        "slug",
        "description",
    )


class ModalityFilter(admin.SimpleListFilter):

    title = _l('Modality')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'modality'

    def lookups(self, request, model_admin):
        return Modality.objects.values_list("pk", "name")

    def queryset(self, request, qs):

        val = self.value()
        if val:
            return qs.filter(modality_id=val)

        return qs


class FaultAdmin(SaveUserQATrackAdmin):

    list_display = (
        "name",
        site_name,
        "unit",
        "modality",
        "get_fault_types",
        "occurred",
    )

    list_filter = (
        SiteFilter,
        "unit",
        ModalityFilter,
        "fault_types",
    )

    list_select_related = [
        "modality",
        "unit",
        "unit__site",
    ]

    list_prefetch_related = [
        "fault_types"
    ]

    def name(self, obj):
        return str(obj)
    name.admin_order_field = "pk"

    def get_fault_types(self, obj):
        return "FAULT TYPES"


class FaultReviewGroupAdmin(BaseQATrackAdmin):

    list_display = ("group", "required")
    search_fields = (
        "group__name",
    )


admin.site.register([models.FaultType], FaultTypeAdmin)
admin.site.register([models.Fault], FaultAdmin)
admin.site.register([models.FaultReviewGroup], FaultReviewGroupAdmin)
