from __future__ import unicode_literals

from django.contrib import admin
import django.forms as forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _l

from qatrack.qatrack_core.admin import BaseQATrackAdmin

from . import models as p_models


class PartAdmin(BaseQATrackAdmin):

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

    def get_cost(self, obj):
        return obj.cost if obj and obj.cost else mark_safe("<em>N/A</em>")
    get_cost.short_description = "Cost"
    get_cost.admin_order_field = "cost"


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


class StorageInline(admin.TabularInline):

    model = p_models.Storage
    form = StorageInlineForm
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


class RoomAdmin(BaseQATrackAdmin):

    list_display = ['name', 'site']
    search_fields = ('name', 'site__name')
    inlines = [StorageInline]
    del_storage_response = None

    class Media:
        js = (
            "admin/js/jquery.init.js",
            'jquery/js/jquery.min.js',
            'autosize/js/autosize.min.js',
        )

    def get_queryset(self, request):
        if request.method == 'POST':
            return super().get_queryset(request).prefetch_related(
                'storage_set',
                'storage_set__room',
                'storage_set__room__site',
            )
        return super().get_queryset(request).prefetch_related('storage_set')


class ContactInlineForm(forms.ModelForm):

    class Meta:
        model = p_models.Contact
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number']


class ContactInline(admin.TabularInline):

    model = p_models.Contact
    form = ContactInlineForm

    def _get_queryset(self, request):

        qs = p_models.Storage.objects.get_queryset_for_room(room=self.parent_instance).prefetch_related(
            'partstoragecollection_set__part', 'partstoragecollection_set'
        ).select_related('room', 'room__site')

        return qs

    def _formfield_for_foreignkey(self, db_field, request, **kwargs):
        if 'queryset' in kwargs:
            kwargs['queryset'] = kwargs['queryset'].select_related('room', 'room__site')
        else:
            db = kwargs.pop('using', None)
            rel = db_field.remote_field
            kwargs['queryset'] = rel.model._default_manager.using(db).complex_filter(
                rel.limit_choices_to
            ).select_related('room', 'room__site')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SupplierAdmin(BaseQATrackAdmin):

    list_display = ['name', 'get_website', 'phone_number']
    search_fields = ('name', 'address')
    inlines = [ContactInline]

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'autosize/js/autosize.min.js',
        )

    def get_website(self, obj):
        return obj.get_website_tag()
    get_website.short_description = _l("Website")
    get_website.admin_order_field = "website"


admin.site.register([p_models.Part], PartAdmin)
admin.site.register([p_models.PartCategory], BaseQATrackAdmin)
admin.site.register([p_models.Supplier], SupplierAdmin)
admin.site.register([p_models.Room], RoomAdmin)
