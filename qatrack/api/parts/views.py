from django.db import transaction
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework_filters import backends

from qatrack.api.parts import filters, serializers
from qatrack.parts import models


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = models.Supplier.objects.all()
    serializer_class = serializers.SupplierSerializer
    filterset_class = filters.SupplierFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )


class StorageViewSet(viewsets.ModelViewSet):
    queryset = models.Storage.objects.all()
    serializer_class = serializers.StorageSerializer
    filterset_class = filters.StorageFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )


class PartCategoryViewSet(viewsets.ModelViewSet):
    queryset = models.PartCategory.objects.all()
    serializer_class = serializers.PartCategorySerializer
    filterset_class = filters.PartCategoryFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )


class PartViewSet(viewsets.ModelViewSet):
    queryset = models.Part.objects.all()
    serializer_class = serializers.PartSerializer
    filterset_class = filters.PartFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )


class PartStorageCollectionViewSet(viewsets.ModelViewSet):
    queryset = models.PartStorageCollection.objects.all()
    serializer_class = serializers.PartStorageCollectionSerializer
    filterset_class = filters.PartStorageCollectionFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )


class PartSupplierCollectionViewSet(viewsets.ModelViewSet):
    queryset = models.PartSupplierCollection.objects.all()
    serializer_class = serializers.PartSupplierCollectionSerializer
    filterset_class = filters.PartSupplierCollectionFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )


class PartUsedViewSet(viewsets.ModelViewSet):
    queryset = models.PartUsed.objects.all()
    serializer_class = serializers.PartUsedSerializer
    filterset_class = filters.PartUsedFilter
    filter_backends = (
        backends.RestFrameworkFilterBackend,
        OrderingFilter,
    )

    @transaction.atomic
    def perform_create(self, serializer):
        instance = serializer.save()
        instance.remove_from_storage()

    @transaction.atomic
    def perform_update(self, serializer):
        old_instance = type(self.get_object()).objects.select_for_update().get(pk=self.kwargs.get('pk') or self.kwargs.get(self.lookup_field))
        old_instance.add_back_to_storage()
        serializer.instance = old_instance
        instance = serializer.save()
        instance.remove_from_storage()
