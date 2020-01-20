from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import ValidationError
import django.forms as forms
from django.utils.safestring import mark_safe

if settings.USE_PARTS:

    from django.contrib import admin

    from . import models as p_models

    class PartAdmin(admin.ModelAdmin):

        list_display = [
            'name',
            'get_part_number',
            'new_or_used',
            'part_category',
            'quantity_min',
            'quantity_current',
            'cost',
        ]
        search_fields = ['name', 'part_number', 'alt_part_number']

        def get_part_number(self, obj):
            return obj.part_number if obj and obj.part_number else mark_safe("<em>N/A</em>")
        get_part_number.short_description = "Part Number"
        get_part_number.admin_order_field = "part_number"


    class StorageInlineFormSet(forms.BaseInlineFormSet):

        model = p_models.Storage

        def clean(self):

            forms_to_delete = self.deleted_forms
            valid_forms = []
            changed_forms = []
            for form in self.forms:
                if form not in forms_to_delete and not form.empty_permitted:
                    if form.is_valid():
                        valid_forms.append(form)
                    if form.has_changed():
                        changed_forms.append(form)

            seen_locations = set()
            for form in valid_forms:
                if form.cleaned_data.get('location', None) in seen_locations:
                    for changed_form in changed_forms:
                        if changed_form.cleaned_data.get('location', None) == form.cleaned_data.get('location', None):
                            changed_form.add_error('location', ValidationError('Location already exists'))

                seen_locations.add(form.cleaned_data.get('location', None))


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

        def validate_unique(self):
            """validate unique moved to formset because it was very inefficient here"""
            pass


    class StorageInline(admin.TabularInline):

        model = p_models.Storage
        form = StorageInlineForm
        formset = StorageInlineFormSet
        parent_instance = None
        template = 'admin/parts/storage/edit_inline/tabular_paginated.html'

        def get_formset(self, request, obj=None, **kwargs):
            if obj:
                self.verbose_name_plural = 'Storage within room %s' % obj.name
                self.parent_instance = obj
            formset = super().get_formset(request, obj=obj, **kwargs)
            return formset

        def get_queryset(self, request):

            qs = p_models.Storage.objects.get_queryset_for_room(room=self.parent_instance).prefetch_related(
                'partstoragecollection_set__part', 'partstoragecollection_set'
            ).select_related('room', 'room__site')

            return qs

        def formfield_for_foreignkey(self, db_field, request, **kwargs):
            if 'queryset' in kwargs:
                kwargs['queryset'] = kwargs['queryset'].select_related('room', 'room__site')
            else:
                db = kwargs.pop('using', None)
                rel = db_field.remote_field
                kwargs['queryset'] = rel.model._default_manager.using(db).complex_filter(
                    rel.limit_choices_to
                ).select_related('room', 'room__site')
            return super().formfield_for_foreignkey(db_field, request, **kwargs)


    class RoomAdmin(admin.ModelAdmin):

        list_display = ['name', 'site']
        search_fields = ('name', 'site__name')
        inlines = [StorageInline]
        del_storage_response = None

        class Media:
            js = (
                settings.STATIC_URL + 'autosize/js/autosize.min.js',
            )

        def get_queryset(self, request):
            if request.method == 'POST':
                return super().get_queryset(request).prefetch_related(
                    'storage_set',
                    'storage_set__room',
                    'storage_set__room__site',
                )
            return super().get_queryset(request).prefetch_related('storage_set')


    admin.site.register([p_models.Part], PartAdmin)
    admin.site.register([p_models.PartCategory], admin.ModelAdmin)
    admin.site.register([p_models.Supplier], admin.ModelAdmin)
    admin.site.register([p_models.Room], RoomAdmin)
