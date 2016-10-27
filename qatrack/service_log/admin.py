
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms import ModelMultipleChoiceField, ModelForm
from django.utils.translation import ugettext as _

from .models import ServiceEventStatus, ServiceType, ProblemType, UnitServiceArea, ServiceArea, ServiceEvent, ThirdParty, Vendor, GroupLinker
from qatrack.units.models import Unit, Modality


class ServiceEventStatusFormAdmin(ModelForm):

    class Meta:
        model = ServiceEventStatus
        fields = '__all__'


class ServiceEventStatusAdmin(admin.ModelAdmin):
    list_display = ["name", "is_review_required", "is_default", "is_active"]
    form = ServiceEventStatusFormAdmin

    class Media:
        js = (
            settings.STATIC_URL + "jquery/js/jquery.min.js",
            settings.STATIC_URL + "colorpicker/js/bootstrap-colorpicker.min.js",
            settings.STATIC_URL + "qatrack_core/js/admin_colourpicker.js",

        )
        css = {
            'all': (
                settings.STATIC_URL + "bootstrap/css/bootstrap.min.css",
                settings.STATIC_URL + "colorpicker/css/bootstrap-colorpicker.min.css",
                settings.STATIC_URL + "qatrack_core/css/admin.css",
            ),
        }


class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_approval_required', 'is_active']


class ProblemTypeAdmin(admin.ModelAdmin):
    list_display = ['name']


class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ['name']
    filter_horizontal = ("units",)


class ServiceEventAdmin(admin.ModelAdmin):
    list_display = ['unit_name', 'service_area_name']

    def unit_name(self, obj):
        return obj.unit_service_area.unit

    def service_area_name(self, obj):
        return obj.unit_service_area.service_area


# Unit admin stuff here to avoid circular dependencies
# Custom model form because filter_horizontal doesn't work with reverse m2m
class UnitFormAdmin(ModelForm):

    service_areas = ModelMultipleChoiceField(
        queryset=ServiceArea.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name=_('Service areas'),
            is_stacked=False
        )
    )
    modalities = ModelMultipleChoiceField(
        queryset=Modality.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name=_('Modalities'),
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
            'restricted',
            'type',
            'site',
            'modalities',
            'service_areas',
        ]

    def __init__(self, *args, **kwargs):
        super(UnitFormAdmin, self).__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['service_areas'].initial = self.instance.service_areas.all()

    def save(self, commit=True):
        unit = super(UnitFormAdmin, self).save(commit=False)
        # unit.service_areas = self.cleaned_data['service_areas']

        if commit:
            unit.save()
            self.save_m2m()

        if unit.pk:
            for sa in self.cleaned_data['service_areas']:
                unit_service_area = UnitServiceArea(unit=unit, service_area=sa)
                unit_service_area.save()

            for usa in UnitServiceArea.objects.filter(unit=unit).exclude(service_area__in=self.cleaned_data['service_areas']):
                usa.delete()

        return unit


class UnitAdmin(admin.ModelAdmin):
    form = UnitFormAdmin


admin.site.register(Unit, UnitAdmin)

admin.site.register(ServiceEvent, ServiceEventAdmin)
admin.site.register(ServiceArea, ServiceAreaAdmin)
admin.site.register(ProblemType, ProblemTypeAdmin)
admin.site.register(ServiceType, ServiceTypeAdmin)
admin.site.register(ServiceEventStatus, ServiceEventStatusAdmin)

admin.site.register([ThirdParty, GroupLinker], admin.ModelAdmin)
