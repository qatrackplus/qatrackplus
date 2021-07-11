import rest_framework_filters as filters

from qatrack.api.service_log.filters import ServiceEventFilter
from qatrack.api.units.filters import StorageFilter
from qatrack.parts import models
from qatrack.service_log.models import ServiceEvent


class SupplierFilter(filters.FilterSet):

    class Meta:
        model = models.Supplier
        fields = {
            "name": "__all__",
            "notes": "__all__",
        }


class PartCategoryFilter(filters.FilterSet):

    class Meta:
        model = models.PartCategory
        fields = {
            "name": "__all__",
        }


class PartFilter(filters.FilterSet):

    part_category = filters.RelatedFilter(
        PartCategoryFilter,
        field_name="part_category",
        queryset=models.PartCategory.objects.all(),
    )
    suppliers = filters.RelatedFilter(SupplierFilter, field_name="suppliers", queryset=models.Supplier.objects.all())
    storage = filters.RelatedFilter(StorageFilter, field_name="storage", queryset=models.Storage.objects.all())

    class Meta:
        model = models.Part
        fields = {
            "part_number": "__all__",
            "alt_part_number": "__all__",
            "name": "__all__",
            "quantity_min": "__all__",
            "quantity_current": "__all__",
            "cost": "__all__",
            "notes": "__all__",
            "is_obsolete": "__all__",
        }


class PartStorageCollectionFilter(filters.FilterSet):

    part = filters.RelatedFilter(PartFilter, field_name="part", queryset=models.Part.objects.all())
    storage = filters.RelatedFilter(StorageFilter, field_name="storage", queryset=models.Storage.objects.all())

    class Meta:
        model = models.PartStorageCollection
        fields = {
            "quantity": "__all__",
        }


class PartSupplierCollectionFilter(filters.FilterSet):

    part = filters.RelatedFilter(PartFilter, field_name="part", queryset=models.Part.objects.all())
    supplier = filters.RelatedFilter(SupplierFilter, field_name="supplier", queryset=models.Supplier.objects.all())

    class Meta:
        model = models.PartSupplierCollection
        fields = {
            "part_number": "__all__",
        }


class PartUsedFilter(filters.FilterSet):

    service_event = filters.RelatedFilter(
        ServiceEventFilter,
        field_name="service_event",
        queryset=ServiceEvent.objects.all(),
    )
    part = filters.RelatedFilter(PartFilter, field_name="part", queryset=models.Part.objects.all())
    from_storage = filters.RelatedFilter(
        StorageFilter, field_name="from_storage", queryset=models.Storage.objects.all()
    )

    class Meta:
        model = models.PartUsed
        fields = {
            "quantity": "__all__",
        }
