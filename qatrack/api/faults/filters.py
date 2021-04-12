import rest_framework_filters as filters

from qatrack.api.filters import MaxDateFilter, MinDateFilter
from qatrack.api.units.filters import (
    ModalityFilter,
    UnitFilter,
)
from qatrack.faults import models
from qatrack.units.models import Modality, Unit


class FaultTypeFilter(filters.FilterSet):

    class Meta:
        model = models.FaultType
        fields = {
            "code": "__all__",
        }


class FaultFilter(filters.FilterSet):

    fault_type = filters.RelatedFilter(
        FaultTypeFilter,
        field_name="fault_type",
        queryset=models.FaultType.objects.all(),
    )
    unit = filters.RelatedFilter(UnitFilter, field_name='unit', queryset=Unit.objects.all())

    modality = filters.RelatedFilter(
        ModalityFilter,
        field_name='modality',
        queryset=Modality.objects.all(),
    )

    occurred_min = MinDateFilter(field_name="occurred")
    occurred_max = MaxDateFilter(field_name="occurred")

    class Meta:
        model = models.Fault
        fields = {
            "occurred": ['exact', "in"],
            "created": ['exact', "in"],
            "modified": ['exact', "in"],
        }
