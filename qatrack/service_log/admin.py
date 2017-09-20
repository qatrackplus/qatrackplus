
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import ObjectDoesNotExist
from django.forms import ModelMultipleChoiceField, ModelForm, DateTimeField
from django.shortcuts import HttpResponseRedirect
from django.utils.translation import ugettext as _

from .models import ServiceEventStatus, ServiceType, UnitServiceArea, ServiceArea, ServiceEvent, ThirdParty, Vendor, GroupLinker
from qatrack.units.models import Unit, Modality, UnitAvailableTime
from .forms import ServiceEventForm, HoursMinDurationField
from qatrack.units.forms import UnitAvailableTimeForm

from admin_views.admin import AdminViews


class ServiceEventStatusFormAdmin(ModelForm):

    class Meta:
        model = ServiceEventStatus
        fields = '__all__'


class DeleteOnlyFromOwnFormAdmin(admin.ModelAdmin):

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return super(DeleteOnlyFromOwnFormAdmin, self).has_delete_permission(request, obj)


class ServiceEventStatusAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name', 'is_review_required', 'is_default', 'rts_qa_must_be_reviewed']
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


class ServiceTypeAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name', 'is_review_required', 'is_active']


class ServiceAreaAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name']
    filter_horizontal = ("units",)


class ServiceEventAdminForm(ModelForm):

    service_event_related = ModelMultipleChoiceField(
        queryset=ServiceEvent.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name=_('Related Service Events'),
            is_stacked=False
        )
    )
    duration_service_time = HoursMinDurationField(label=_('Service time'), required=False)
    duration_lost_time = HoursMinDurationField(label=_('Lost time'), required=False)

    datetime_service = DateTimeField()

    class Meta:
        model = ServiceEvent

        fields = [
            'datetime_service', 'unit_service_area', 'service_type', 'service_status',
            'problem_description', 'service_event_related', 'work_description',
            'safety_precautions', 'duration_service_time', 'duration_lost_time'
        ]

    def __init__(self, *args, **kwargs):
        super(ServiceEventAdminForm, self).__init__(*args, **kwargs)

        datetime_service = self.fields['datetime_service']
        datetime_service.widget.attrs['class'] = 'daterangepicker-input'
        datetime_service.widget.format = settings.INPUT_DATE_FORMATS[0]
        datetime_service.input_formats = settings.INPUT_DATE_FORMATS
        datetime_service.widget.attrs["title"] = settings.DATETIME_HELP
        datetime_service.help_text = settings.DATETIME_HELP


class ServiceEventAdmin(DeleteOnlyFromOwnFormAdmin):

    list_display = ['pk', 'datetime_service', 'unit_name', 'service_area_name']
    form = ServiceEventAdminForm

    def unit_name(self, obj):
        return obj.unit_service_area.unit

    def service_area_name(self, obj):
        return obj.unit_service_area.service_area

    class Media:
        js = (
            settings.STATIC_URL + "jquery/js/jquery.min.js",
            settings.STATIC_URL + 'moment/js/moment.min.js',
            settings.STATIC_URL + 'daterangepicker/js/daterangepicker.js',
            settings.STATIC_URL + "inputmask/js/inputmask.js",
            settings.STATIC_URL + 'inputmask/js/jquery.inputmask.js',
            settings.STATIC_URL + "inputmask/js/inputmask.dependencyLib.jquery.js",
            settings.STATIC_URL + 'service_log/js/sl_admin_serviceevent.js'
        )
        css = {
            'all': (
                settings.STATIC_URL + "bootstrap/css/bootstrap.min.css",
                settings.STATIC_URL + 'daterangepicker/css/daterangepicker.css',
                settings.STATIC_URL + "qatrack_core/css/admin.css",
            ),
        }


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

        if commit:
            unit.save()
            self.save_m2m()

        if unit.pk:
            for sa in self.cleaned_data['service_areas']:
                unit_service_area, created = UnitServiceArea.objects.get_or_create(unit=unit, service_area=sa)
                # unit_service_area.save()

            for usa in UnitServiceArea.objects.filter(unit=unit).exclude(service_area__in=self.cleaned_data['service_areas']):
                usa.delete()

        return unit

    def form_valid(self, request, queryset, form):
        print('forms valid---------')
        return super(UnitFormAdmin, self).form_valid(request, queryset, form)


class UnitAdmin(admin.ModelAdmin):
    form = UnitFormAdmin
    list_display = ['pk', 'name', 'number', 'active', 'type', 'site']
    list_filter = ['active', 'site', 'modalities']

    class Media:
        js = (
            settings.STATIC_URL + 'jquery/js/jquery.min.js',
            settings.STATIC_URL + 'inputmask/js/jquery.inputmask.bundle.js',
        )
        css = {
            'all': (
                settings.STATIC_URL + 'units/css/admin.css',
            ),
        }

    def change_view(self, request, object_id, form_url='', extra_context=None):

        extra_context = extra_context or {}

        form_kwargs = {}
        if object_id:
            form_kwargs['instance'] = UnitAvailableTime.objects.filter(unit=object_id).latest()
        if request.method == 'POST':
            form_kwargs['data'] = request.POST

        if 'available_time_form' not in extra_context:
            extra_context['available_time_form'] = UnitAvailableTimeForm(**form_kwargs)
            extra_context['available_time_form'].fields['units'].initial = [object_id]

        if request.method == 'POST':

            uatf = extra_context['available_time_form']
            if not uatf.is_valid():
                request.method = 'GET'
                return self.change_view(request, object_id, form_url, extra_context)
            else:
                try:
                    uat = UnitAvailableTime.objects.get(date_changed=uatf.cleaned_data['date_changed'], unit=object_id)

                    uat.hours_monday = uatf.cleaned_data['hours_monday']
                    uat.hours_tuesday = uatf.cleaned_data['hours_tuesday']
                    uat.hours_wednesday = uatf.cleaned_data['hours_wednesday']
                    uat.hours_thursday = uatf.cleaned_data['hours_thursday']
                    uat.hours_friday = uatf.cleaned_data['hours_friday']
                    uat.hours_saturday = uatf.cleaned_data['hours_saturday']
                    uat.hours_sunday = uatf.cleaned_data['hours_sunday']
                    uat.save()
                except ObjectDoesNotExist:
                    UnitAvailableTime.objects.create(
                        date_changed=uatf.cleaned_data['date_changed'],
                        unit=object_id,
                        hours_monday=uatf.cleaned_data['hours_monday'],
                        hours_tuesday=uatf.cleaned_data['hours_tuesday'],
                        hours_wednesday=uatf.cleaned_data['hours_wednesday'],
                        hours_thursday=uatf.cleaned_data['hours_thursday'],
                        hours_friday=uatf.cleaned_data['hours_friday'],
                        hours_saturday=uatf.cleaned_data['hours_saturday'],
                        hours_sunday=uatf.cleaned_data['hours_sunday']
                    )

        else:
            print('Not posting')

        return super(UnitAdmin, self).change_view(request, object_id, form_url='', extra_context=extra_context)


admin.site.register(Unit, UnitAdmin)

admin.site.register(ServiceEvent, ServiceEventAdmin)
admin.site.register(ServiceArea, ServiceAreaAdmin)
# admin.site.register(ProblemType, ProblemTypeAdmin)
admin.site.register(ServiceType, ServiceTypeAdmin)
admin.site.register(ServiceEventStatus, ServiceEventStatusAdmin)

admin.site.register([ThirdParty, GroupLinker, UnitServiceArea], admin.ModelAdmin)
