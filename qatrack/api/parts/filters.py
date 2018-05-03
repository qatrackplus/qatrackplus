import rest_framework_filters as filters

from qatrack.api.service_log.filters import ServiceEventFilter
from qatrack.api.units.filters import SiteFilter
from qatrack.parts import models
from qatrack.service_log.models import ServiceEvent
from qatrack.units.models import Site


class SupplierFilter(filters.FilterSet):

    class Meta:
        model = models.Supplier
        fields = {
            "name": "__all__",
            "notes": "__all__",
        }


class RoomFilter(filters.FilterSet):

    site = filters.RelatedFilter(SiteFilter, name="site", queryset=Site.objects.all())

    class Meta:
        model = models.Room
        fields = {
            "name": "__all__",
        }


class StorageFilter(filters.FilterSet):

    room = filters.RelatedFilter(RoomFilter, name="room", queryset=models.Room.objects.all())

    class Meta:
        model = models.Storage
        fields = {
            "location": "__all__",
            "description": "__all__",
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
        name="part_category",
        queryset=models.PartCategory.objects.all(),
    )
    suppliers = filters.RelatedFilter(SupplierFilter, name="suppliers", queryset=models.Supplier.objects.all())
    storage = filters.RelatedFilter(StorageFilter, name="storage", queryset=models.Storage.objects.all())

    class Meta:
        model = models.Part
        fields = {
            "part_number": "__all__",
            "alt_part_number": "__all__",
            "description": "__all__",
            "quantity_min": "__all__",
            "quantity_current": "__all__",
            "cost": "__all__",
            "notes": "__all__",
            "is_obsolete": "__all__",
        }


class PartStorageCollectionFilter(filters.FilterSet):

    part = filters.RelatedFilter(PartFilter, name="part", queryset=models.Part.objects.all())
    storage = filters.RelatedFilter(StorageFilter, name="storage", queryset=models.Storage.objects.all())

    class Meta:
        model = models.PartStorageCollection
        fields = {
            "quantity": "__all__",
        }


class PartSupplierCollectionFilter(filters.FilterSet):

    part = filters.RelatedFilter(PartFilter, name="part", queryset=models.Part.objects.all())
    supplier = filters.RelatedFilter(SupplierFilter, name="supplier", queryset=models.Supplier.objects.all())

    class Meta:
        model = models.PartSupplierCollection
        fields = {
            "part_number": "__all__",
        }


class PartUsedFilter(filters.FilterSet):

    service_event = filters.RelatedFilter(ServiceEventFilter, name="service_event", queryset=ServiceEvent.objects.all())
    part = filters.RelatedFilter(PartFilter, name="part", queryset=models.Part.objects.all())
    from_storage = filters.RelatedFilter(StorageFilter, name="from_storage", queryset=models.Storage.objects.all())

    class Meta:
        model = models.PartUsed
        fields = {
            "quantity": "__all__",
        }
