
from django.conf import settings
from django.core.exceptions import ValidationError
import django.forms as forms

if settings.USE_PARTS:
    from django.contrib import admin

    from . import models as p_models


    class PartAdmin(admin.ModelAdmin):

        list_display = ['part_number', 'quantity_min', 'quantity_current', 'description', 'cost']
        search_fields = ['part_number', 'description']


    class StorageInlineForm(forms.ModelForm):

        class Meta:
            model = p_models.Storage
            fields = ['id', 'room', 'location', 'description']

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['description'].widget.attrs.update({'rows': 1, 'class': 'autosize width-100'})
            if self.instance.pk and self.initial['location'] is None:
                self.fields['location'].widget.attrs.update({'placeholder': '<no specific location>'})
                self.fields['location'].disabled = 'disabled'

        def clean(self):
            cleaned = super().clean()
            location = cleaned.get('location')
            room = self.cleaned_data.get('room')
            if self.instance.pk is None and p_models.Storage.objects.filter(room=room, location=location).exists():
                self.add_error('location', ValidationError('Location already exists'))
            return cleaned


    class StorageInline(admin.TabularInline):

        model = p_models.Storage
        form = StorageInlineForm
        parent_instance = None
        template = 'admin/parts/storage/edit_inline/tabular_paginated.html'

        def get_formset(self, request, obj=None, **kwargs):
            if obj:
                self.verbose_name_plural = 'Storage within room %s' % obj.name
                self.parent_instance = obj
            return super().get_formset(request, obj=obj, **kwargs)

        def get_queryset(self, request):
            qs = super().get_queryset(request).filter().prefetch_related(
                'partstoragecollection_set__part', 'partstoragecollection_set'
            )
            return qs


    class RoomAdmin(admin.ModelAdmin):

        list_display = ['name', 'site']
        search_fields = ('name', 'site__name')
        inlines = [StorageInline]
        del_storage_response = None

        class Media:
            js = (
                settings.STATIC_URL + 'autosize/js/autosize.min.js',
            )


    admin.site.register([p_models.Part], PartAdmin)
    admin.site.register([p_models.PartCategory], admin.ModelAdmin)
    admin.site.register([p_models.Supplier], admin.ModelAdmin)
    admin.site.register([p_models.Room], RoomAdmin)