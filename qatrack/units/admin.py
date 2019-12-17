from itertools import groupby

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms import ChoiceField, ModelForm, ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _l

from qatrack.service_log.models import (
    ServiceArea,
    ServiceEvent,
    UnitServiceArea,
)

from .forms import UnitAvailableTimeForm
from .models import (
    Modality,
    Site,
    Unit,
    UnitAvailableTime,
    UnitClass,
    UnitType,
    Vendor,
)


class UnitFormAdmin(ModelForm):

    type = ChoiceField(label=_l("Unit Type"))

    if settings.USE_SERVICE_LOG:
        service_areas = ModelMultipleChoiceField(
            queryset=ServiceArea.objects.all(),
            required=False,
            widget=FilteredSelectMultiple(
                verbose_name=_l('Service areas'),
                is_stacked=False
            )
        )
    modalities = ModelMultipleChoiceField(
        queryset=Modality.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name=_l('Modalities'),
            is_stacked=False
        )
    )

    class Meta:
        model = Unit

        fields = [
            'number',
            'name',
            'serial_number',
            'location',
            'install_date',
            'date_acceptance',
            'active',
            'type',
            'site',
            'modalities',
        ]
        if settings.USE_SERVICE_LOG:
            fields.append('service_areas')
            fields.insert(8, 'is_serviceable')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if settings.USE_SERVICE_LOG and self.instance and self.instance.pk:
            self.fields['service_areas'].initial = self.instance.service_areas.all()

        if Site.objects.count() == 1 and not self.instance.pk:
            self.fields['site'].initial = Site.objects.first()

        def vendor_name(ut):
            return ut.vendor.name if ut.vendor else "Other"

        def vendor_unit_type(ut):
            return "%s :: %s" % (ut.vendor.name if ut.vendor else "Other", ut.name)

        unit_types = UnitType.objects.order_by("vendor__name", "name")
        choices = [(v, list(uts)) for (v, uts) in groupby(unit_types, key=vendor_name)]
        choices = [(v, [(ut.id, vendor_unit_type(ut)) for ut in uts]) for (v, uts) in choices]
        choices = [("", "---------")] + choices

        self.fields['type'].choices = choices

    def clean_type(self):
        utype = self.cleaned_data.get('type')
        if utype:
            utype = UnitType.objects.get(pk=utype)
        return utype

    def clean_service_areas(self):
        service_areas = self.cleaned_data['service_areas']

        if self.instance:
            unit = self.instance

            for usa in UnitServiceArea.objects.filter(unit=unit).exclude(service_area__in=service_areas):
                if ServiceEvent.objects.filter(unit_service_area=usa).exists():
                    data_copy = self.data.copy()
                    data_copy.setlist(
                        'service_areas',
                        [str(sa.id) for sa in (service_areas | ServiceArea.objects.filter(pk=usa.service_area_id))]
                    )
                    self.data = data_copy
                    self.add_error(
                        'service_areas',
                        (
                            'Cannot remove {} from unit {}. '
                            'There exists Service Event(s) with that Unit and Service Area.'
                        ).format(usa.service_area.name, unit.name)
                    )

        return service_areas

    def save(self, commit=True):

        unit = super().save(commit=commit)
        unit.save()

        if settings.USE_SERVICE_LOG:
            service_areas = self.cleaned_data['service_areas']

            for sa in service_areas:
                UnitServiceArea.objects.get_or_create(unit=unit, service_area=sa)

            for usa in UnitServiceArea.objects.filter(unit=unit).exclude(service_area__in=service_areas):
                if not ServiceEvent.objects.filter(unit_service_area=usa).exists():
                    usa.delete()

        return unit


class UnitAvailableTimeInline(admin.TabularInline):

    model = UnitAvailableTime
    form = UnitAvailableTimeForm
    extra = 2
    ordering = ['date_changed']
    verbose_name_plural = 'Unit Schedule'


class UnitAdmin(admin.ModelAdmin):

    form = UnitFormAdmin
    list_display = ['name', 'number', 'active', 'type', 'site', 'is_serviceable']
    list_filter = ['active', 'site', 'modalities', 'type__unit_class']
    list_editable = ['site', 'is_serviceable']
    ordering = ['number']
    search_fields = ['number', 'name']

    save_as = True

    if settings.USE_SERVICE_LOG:
        inlines = [UnitAvailableTimeInline]

    class Media:
        js = (
            settings.STATIC_URL + 'jquery/js/jquery.min.js',
            settings.STATIC_URL + 'inputmask/js/jquery.inputmask.bundle.min.js',
        )
        css = {
            'all': (
                settings.STATIC_URL + 'units/css/admin.css',
            ),
        }

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('site', 'type')


class UnitTypeAdmin(admin.ModelAdmin):

    list_display = ['model_name', 'vendor', 'unit_class']
    list_filter = ['unit_class', 'vendor']
    list_editable = ['unit_class', 'vendor']

    def get_queryset(self, request):
        return super(UnitTypeAdmin, self).get_queryset(request).select_related(
            "vendor",
            "unit_class",
        )

    def model_name(self, obj):
        model = ' - {}'.format(obj.model) if obj.model else ''
        vendor_name = '{}: '.format(obj.vendor.name) if obj.vendor else ''
        return "{}{}{}".format(vendor_name, obj.name, model)


class ModalityAdmin(admin.ModelAdmin):

    list_display = ["name"]


class SiteAdmin(admin.ModelAdmin):
    """QC categories admin"""
    prepopulated_fields = {'slug': ('name',)}
    list_display = (
        "name",
        "slug"
    )


admin.site.register(Unit, UnitAdmin)
admin.site.register(UnitType, UnitTypeAdmin)
admin.site.register(Modality, ModalityAdmin)
admin.site.register(Site, SiteAdmin)
admin.site.register([UnitClass, Vendor], admin.ModelAdmin)
