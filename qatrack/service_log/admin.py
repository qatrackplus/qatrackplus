
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.exceptions import DisallowedModelAdminToField
from django.contrib.admin.options import TO_FIELD_VAR, IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import PermissionDenied
from django.db.models import ObjectDoesNotExist
from django.forms import ModelMultipleChoiceField, ModelForm, DateTimeField, ValidationError
from django.forms.formsets import all_valid
from django.http import Http404
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.translation import ugettext as _

from .models import ServiceEventStatus, ServiceType, UnitServiceArea, ServiceArea, ServiceEvent, ThirdParty, Vendor, GroupLinker
from qatrack.units.models import Unit, Modality, UnitAvailableTime
from qatrack.units.forms import UnitAvailableTimeForm


class ServiceEventStatusFormAdmin(ModelForm):

    class Meta:
        model = ServiceEventStatus
        fields = '__all__'

    def clean_is_default(self):
        is_default = self.cleaned_data['is_default']
        if not is_default and self.initial['is_default']:
            raise ValidationError('There must be one default status. Edit another status to be default first.')
        return is_default


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

    def delete_view(self, request, object_id, extra_context=None):

        if ServiceEventStatus.objects.get(pk=object_id).is_default:
            extra_context = extra_context or {'is_default': True}

        return super().delete_view(request, object_id, extra_context)


class ServiceTypeAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name', 'is_review_required', 'is_active']


class ServiceAreaAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name']
    filter_horizontal = ("units",)


# class ServiceEventAdminForm(ModelForm):
#
#     service_event_related = ModelMultipleChoiceField(
#         queryset=ServiceEvent.objects.none(),
#         required=False,
#         widget=FilteredSelectMultiple(
#             verbose_name=_('Related Service Events'),
#             is_stacked=False
#         )
#     )
#     duration_service_time = HoursMinDurationField(label=_('Service time'), required=False)
#     duration_lost_time = HoursMinDurationField(label=_('Lost time'), required=False)
#
#     datetime_service = DateTimeField()
#
#     class Meta:
#         model = ServiceEvent
#
#         fields = [
#             'datetime_service',
#             'unit_service_area',
#             'service_type', 'service_status',
#             'problem_description', 'service_event_related', 'work_description',
#             'safety_precautions', 'duration_service_time', 'duration_lost_time'
#         ]
#
#     def __init__(self, *args, **kwargs):
#         super(ServiceEventAdminForm, self).__init__(*args, **kwargs)
#
#         self.fields['unit_service_area'].queryset = UnitServiceArea.objects.all().select_related('unit', 'service_area')
#         if self.instance.pk:
#             self.fields['service_event_related'].queryset = ServiceEvent.objects.filter(
#                 unit_service_area__unit=self.instance.unit_service_area.unit
#             ).select_related('unit_service_area__unit', 'unit_service_area__service_area')
#
#         datetime_service = self.fields['datetime_service']
#         datetime_service.widget.attrs['class'] = 'daterangepicker-input'
#         datetime_service.widget.format = settings.INPUT_DATE_FORMATS[0]
#         datetime_service.input_formats = settings.INPUT_DATE_FORMATS
#         datetime_service.widget.attrs["title"] = settings.DATETIME_HELP
#         datetime_service.help_text = settings.DATETIME_HELP
#
#
# class ServiceEventAdmin(DeleteOnlyFromOwnFormAdmin):
#
#     list_display = ['pk', 'datetime_service', 'unit_name', 'service_area_name']
#     form = ServiceEventAdminForm
#     list_select_related = ['unit_service_area__unit', 'unit_service_area__service_area']
#
#     def unit_name(self, obj):
#         return obj.unit_service_area.unit.name
#
#     def service_area_name(self, obj):
#         return obj.unit_service_area.service_area.name
#
#     class Media:
#         js = (
#             settings.STATIC_URL + "jquery/js/jquery.min.js",
#             settings.STATIC_URL + 'moment/js/moment.min.js',
#             settings.STATIC_URL + 'daterangepicker/js/daterangepicker.js',
#             # settings.STATIC_URL + "inputmask/js/inputmask.js",
#             settings.STATIC_URL + 'inputmask/js/jquery.inputmask.bundle.js',
#             # settings.STATIC_URL + "inputmask/js/inputmask.dependencyLib.jquery.js",
#             settings.STATIC_URL + 'service_log/js/sl_admin_serviceevent.js'
#         )
#         css = {
#             'all': (
#                 settings.STATIC_URL + "bootstrap/css/bootstrap.min.css",
#                 settings.STATIC_URL + 'daterangepicker/css/daterangepicker.css',
#                 settings.STATIC_URL + "qatrack_core/css/admin.css",
#             ),
#         }


# Unit admin stuff here to avoid circular dependencies
# Custom model form because filter_horizontal doesn't work with reverse m2m
class UnitFormAdmin(ModelForm):

    service_areas = ModelMultipleChoiceField(
        queryset=ServiceArea.objects.all(),
        required=True,
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
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['service_areas'].initial = self.instance.service_areas.all()

    def clean_service_areas(self):
        if self.instance:
            unit = self.instance
            for usa in UnitServiceArea.objects.filter(unit=unit).exclude(service_area__in=self.cleaned_data['service_areas']):
                if ServiceEvent.objects.filter(unit_service_area=usa).exists():
                    data_copy = self.data.copy()
                    data_copy.setlist('service_areas', [str(sa.id) for sa in (self.cleaned_data['service_areas'] | ServiceArea.objects.filter(pk=usa.service_area_id))])
                    self.data = data_copy
                    raise ValidationError('Cannot remove %s from unit %s. There exists Service Event(s) with that Unit and Service Area.' % (usa.service_area.name, unit.name))

        return self.cleaned_data['service_areas']


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

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        # def change_view(self, request, object_id, form_url='', extra_context=None):

        extra_context = extra_context or {}

        form_kwargs = {}
        if object_id:
            form_kwargs['instance'] = UnitAvailableTime.objects.filter(unit=object_id).latest()
        if request.method == 'POST':
            form_kwargs['data'] = request.POST

        if 'available_time_form' not in extra_context:
            extra_context['available_time_form'] = UnitAvailableTimeForm(**form_kwargs)
            if object_id:
                extra_context['available_time_form'].fields['units'].initial = [object_id]

        to_field = request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))
        if to_field and not self.to_field_allowed(request, to_field):
            raise DisallowedModelAdminToField("The field %s cannot be referenced." % to_field)

        model = self.model
        opts = model._meta

        if request.method == 'POST' and '_saveasnew' in request.POST:
            object_id = None
        add = object_id is None

        if add:
            if not self.has_add_permission(request):
                raise PermissionDenied
            obj = None
        else:
            obj = self.get_object(request, unquote(object_id), to_field)
            if not self.has_change_permission(request, obj):
                raise PermissionDenied

            if obj is None:
                raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {
                    'name': force_text(opts.verbose_name), 'key': escape(object_id)})

        UnitForm = self.get_form(request, obj)
        uatf = extra_context['available_time_form']

        if request.method == 'POST':
            form = UnitForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=not add)
            else:
                form_validated = False
                new_object = form.instance
            formsets, inline_instances = self._create_formsets(request, new_object, change=not add)

            if not uatf.is_valid():
                form_validated = False
                # new_object = form.instance

            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, not add)
                self.save_related(request, form, formsets, not add)

                for sa in form.cleaned_data['service_areas']:
                    unit_service_area, created = UnitServiceArea.objects.get_or_create(unit=new_object, service_area=sa)
                    unit_service_area.save()

                for usa in UnitServiceArea.objects.filter(unit=new_object).exclude(service_area__in=form.cleaned_data['service_areas']):
                    if not ServiceEvent.objects.filter(unit_service_area=usa).exists():
                        usa.delete()

                change_message = self.construct_change_message(request, form, formsets, add)

                try:
                    uat = UnitAvailableTime.objects.get(date_changed=uatf.cleaned_data['date_changed'], unit=new_object)

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
                        unit=new_object,
                        hours_monday=uatf.cleaned_data['hours_monday'],
                        hours_tuesday=uatf.cleaned_data['hours_tuesday'],
                        hours_wednesday=uatf.cleaned_data['hours_wednesday'],
                        hours_thursday=uatf.cleaned_data['hours_thursday'],
                        hours_friday=uatf.cleaned_data['hours_friday'],
                        hours_saturday=uatf.cleaned_data['hours_saturday'],
                        hours_sunday=uatf.cleaned_data['hours_sunday']
                    )

                if add:
                    self.log_addition(request, new_object, change_message)
                    return self.response_add(request, new_object)
                else:
                    self.log_change(request, new_object, change_message)
                    return self.response_change(request, new_object)
            else:
                form_validated = False

        else:
            if add:
                initial = self.get_changeform_initial_data(request)
                form = UnitForm(initial=initial)
                formsets, inline_instances = self._create_formsets(request, form.instance, change=False)
            else:
                form = UnitForm(instance=obj)
                formsets, inline_instances = self._create_formsets(request, obj, change=True)

        adminForm = helpers.AdminForm(
            form,
            list(self.get_fieldsets(request, obj)),
            self.get_prepopulated_fields(request, obj),
            self.get_readonly_fields(request, obj),
            model_admin=self)
        media = self.media + adminForm.media

        inline_formsets = self.get_inline_formsets(request, formsets, inline_instances, obj)
        for inline_formset in inline_formsets:
            media = media + inline_formset.media

        err_list = helpers.AdminErrorList(form, formsets)
        for el in helpers.AdminErrorList(uatf, []):
            err_list.append(el)

        context = dict(
            self.admin_site.each_context(request),
            title=(_('Add %s') if add else _('Change %s')) % force_text(opts.verbose_name),
            adminform=adminForm,
            object_id=object_id,
            original=obj,
            is_popup=(IS_POPUP_VAR in request.POST or
                      IS_POPUP_VAR in request.GET),
            to_field=to_field,
            media=media,
            inline_admin_formsets=inline_formsets,
            errors=err_list,
            preserved_filters=self.get_preserved_filters(request),
        )

        # Hide the "Save" and "Save and continue" buttons if "Save as New" was
        # previously chosen to prevent the interface from getting confusing.
        if request.method == 'POST' and not form_validated and "_saveasnew" in request.POST:
            context['show_save'] = False
            context['show_save_and_continue'] = False
            # Use the change template instead of the add template.
            add = False

        context.update(extra_context or {})

        return self.render_change_form(request, context, add=add, change=not add, obj=obj, form_url=form_url)


admin.site.register(Unit, UnitAdmin)

# admin.site.register(ServiceEvent, ServiceEventAdmin)
admin.site.register(ServiceArea, ServiceAreaAdmin)
# admin.site.register(ProblemType, ProblemTypeAdmin)
admin.site.register(ServiceType, ServiceTypeAdmin)
admin.site.register(ServiceEventStatus, ServiceEventStatusAdmin)

admin.site.register([ThirdParty, GroupLinker, UnitServiceArea], admin.ModelAdmin)
