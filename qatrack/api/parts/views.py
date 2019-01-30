from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework_filters import backends

from qatrack.api.parts import filters, serializers
from qatrack.parts import models


class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Supplier.objects.all()
    serializer_class = serializers.SupplierSerializer
    filterset_class = filters.SupplierFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class StorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Storage.objects.all()
    serializer_class = serializers.StorageSerializer
    filterset_class = filters.StorageFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class PartCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.PartCategory.objects.all()
    serializer_class = serializers.PartCategorySerializer
    filterset_class = filters.PartCategoryFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class PartViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Part.objects.all()
    serializer_class = serializers.PartSerializer
    filterset_class = filters.PartFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class PartStorageCollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.PartStorageCollection.objects.all()
    serializer_class = serializers.PartStorageCollectionSerializer
    filterset_class = filters.PartStorageCollectionFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class PartSupplierCollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.PartSupplierCollection.objects.all()
    serializer_class = serializers.PartSupplierCollectionSerializer
    filterset_class = filters.PartSupplierCollectionFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)


class PartUsedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.PartUsed.objects.all()
    serializer_class = serializers.PartUsedSerializer
    filterset_class = filters.PartUsedFilter
    filter_backends = (backends.RestFrameworkFilterBackend, OrderingFilter,)
