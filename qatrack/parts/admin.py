
from django.conf import settings

if settings.USE_PARTS:
    from django.contrib import admin

    from . import models as p_models


    class PartAdmin(admin.ModelAdmin):

        list_display = ['id', 'part_number', 'quantity_min', 'quantity_current', 'description', 'cost']
        search_fields = ['part_number', 'description']


    class StorageAdmin(admin.ModelAdmin):
        list_display = ['id', 'room', 'location', 'description']
        search_fields = ['room', 'cabinet', 'shelf']


    class PartStorageCollectionAdmin(admin.ModelAdmin):
        list_display = ['id', 'part', 'storage', 'unit', 'quantity']

        def get_queryset(self, request):
            return super(PartStorageCollectionAdmin, self).get_queryset(request).select_related('storage__room', 'storage__room__site')


    admin.site.register([p_models.Part], PartAdmin)
    admin.site.register([p_models.Storage], StorageAdmin)
    admin.site.register([p_models.PartStorageCollection], PartStorageCollectionAdmin)
    admin.site.register([p_models.Supplier, p_models.Room], admin.ModelAdmin)
