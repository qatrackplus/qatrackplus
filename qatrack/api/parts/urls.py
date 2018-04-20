from django.conf.urls import include, url
from rest_framework import routers

from qatrack.api.parts import views

router = routers.DefaultRouter()
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'storages', views.StorageViewSet)
router.register(r'partcategories', views.PartCategoryViewSet)
router.register(r'parts', views.PartViewSet)
router.register(r'partstoragecollections', views.PartStorageCollectionViewSet)
router.register(r'partsuppliercollections', views.PartSupplierCollectionViewSet)
router.register(r'partuseds', views.PartUsedViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
