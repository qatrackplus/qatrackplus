from django import forms
from django.contrib import admin
from django.db.models import Count, Max
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from qatrack.qa import admin as q_admin
from qatrack.qa.admin import assigned_to_name, freq_name
from qatrack.qatrack_core.admin import BaseQATrackAdmin, SaveUserQATrackAdmin
from qatrack.qatrack_core.widgets import DataSelect
from qatrack.units.forms import unit_site_service_area_choices

from .models import (
    GroupLinker,
    ServiceArea,
    ServiceEvent,
    ServiceEventSchedule,
    ServiceEventStatus,
    ServiceEventTemplate,
    ServiceType,
    ThirdParty,
    UnitServiceArea,
)


class ServiceEventStatusFormAdmin(forms.ModelForm):

    class Meta:
        model = ServiceEventStatus
        fields = '__all__'

    def clean_is_default(self):

        is_default = self.cleaned_data['is_default']
        if not is_default and self.initial.get('is_default', False):
            raise forms.ValidationError('There must be one default status. Edit another status to be default first.')
        elif not ServiceEventStatus.objects.filter(is_default=True).first():
            is_default = True
        return is_default


class DeleteOnlyFromOwnFormAdmin(BaseQATrackAdmin):

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return super(DeleteOnlyFromOwnFormAdmin, self).has_delete_permission(request, obj)


class UnitServiceAreaFilter(admin.SimpleListFilter):

    title = _l('Unit Service Area')
    parameter_name = "unit_service_area"

    def lookups(self, request, model_admin):
        qs = UnitServiceArea.objects.select_related('unit', 'service_area')
        return [(usa.pk, str(usa)) for usa in qs]

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(unit_service_area=self.value())

        return queryset


class ServiceEventAdmin(DeleteOnlyFromOwnFormAdmin):

    list_display = [
        "get_se_id",
        "unit_service_area",
        "service_type",
        "service_status",
        "datetime_created",
        "datetime_modified",
        "is_review_required",
        "is_active",
    ]

    list_filter = [UnitServiceAreaFilter, "service_type", "is_review_required", "is_active"]

    raw_id_fields = [
        "test_list_instance_initiated_by",
    ]

    filter_horizontal = ["service_event_related"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "unit_service_area":
            kwargs['queryset'] = UnitServiceArea.objects.select_related("unit", "service_area")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_se_id(self, obj):
        return "Service Event #%d" % obj.pk

    def get_queryset(self, request):

        qs = self.model.all_objects.get_queryset()

        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)

        qs = qs.select_related(
            "unit_service_area",
            "unit_service_area__service_area",
            "unit_service_area__unit",
            "service_status",
            "service_type",
        )
        return qs


class ServiceEventStatusAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name', 'is_review_required', 'is_default', 'rts_qa_must_be_reviewed', 'order']
    list_editable = ['order']
    form = ServiceEventStatusFormAdmin

    class Media:
        js = (
            'admin/js/jquery.init.js',
            "jquery/js/jquery.min.js",
            "colorpicker/js/bootstrap-colorpicker.min.js",
            "qatrack_core/js/admin_colourpicker.js",

        )
        css = {
            'all': (
                "bootstrap/css/bootstrap.min.css",
                "colorpicker/css/bootstrap-colorpicker.min.css",
                "qatrack_core/css/admin.css",
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


class UnitServiceAreaAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['__str__', 'notes']
    list_filter = ['unit', 'service_area']
    search_fields = ['unit__name', 'service_area__name']


class GroupLinkerAdminForm(forms.ModelForm):

    class Meta:
        model = GroupLinker
        fields = '__all__'

    def clean_multiple(self):
        # check if this group linker has cases where there are already multiple group linker instances
        # pointing to it, and if so, don't allow disabling of multiple
        multiple = self.cleaned_data.get("multiple")
        if self.instance and not multiple:
            max_counts = self.instance.grouplinkerinstance_set.values(
                "service_event_id",
            ).annotate(
                counts=Count("service_event_id"),
            ).order_by(
                "counts",
            ).aggregate(max_counts=Max("counts"))['max_counts']
            if max_counts and max_counts > 1:
                raise forms.ValidationError(
                    'You can not disable "multiple" for since there are Service Events'
                    'with multiple Group Linker Instances referring to this Group Linker'
                )
        return multiple


class GroupLinkerAdmin(DeleteOnlyFromOwnFormAdmin):
    list_display = ['name', 'group', 'required', 'multiple', 'description', 'help_text']
    list_filter = ['group']
    search_fields = ['name', 'group__name']

    form = GroupLinkerAdminForm


class SEScheduleSiteFilter(q_admin.SiteFilter):

    title = _l('Site')
    parameter_name = "sitefilter"

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(unit_service_area__unit__site=self.value())

        return queryset


class SEScheduleUnitFilter(q_admin.UnitFilter):

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(unit_service_area__unit=self.value())

        return queryset


class SEScheduleServiceTypeFilter(admin.SimpleListFilter):

    title = _l('Service Type')
    parameter_name = "service_type"

    def lookups(self, request, model_admin):
        return ServiceType.objects.values_list('pk', 'name')

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(service_event_template__service_type=self.value())

        return queryset


class ServiceEventScheduleAdminForm(forms.ModelForm):

    unit = forms.CharField(
        required=False,
        widget=forms.widgets.TextInput(attrs={
            'readonly': 'readonly',
            'disabled': 'disabled'
        }),
    )

    class Meta:
        model = ServiceEventSchedule
        fields = [
            'unit',
            'unit_service_area',
            'frequency',
            'due_date',
            'auto_schedule',
            'assigned_to',
            'visible_to',
            'active',
            'service_event_template',
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # set the service area id as a data attribute on the USA options
        data = {'data-service_area': {'': ''}}
        for usa_id, sa_id in UnitServiceArea.objects.values_list("pk", "service_area_id"):
            data['data-service_area'][usa_id] = sa_id
        usa_choices = unit_site_service_area_choices(include_empty=True, include_unspecified=True)
        self.fields['unit_service_area'].choices = usa_choices
        self.fields['unit_service_area'].widget = DataSelect(choices=usa_choices, data=data)

        # set the service area as a data attribute on the Service Template options
        qs = ServiceEventTemplate.objects.all()
        data = {'data-service_area': {'': ''}}
        for st_id, sa_id in qs.values_list("pk", "service_area_id"):
            data['data-service_area'][st_id] = sa_id if sa_id else ''

        choices = [("", "---------")]
        for pk, template, sa in qs.values_list("pk", "name", "service_area__name"):
            label = "%s (Service Area=%s)" % (template, sa if sa else _("Not Specified"))
            choices.append((pk, label))
        self.fields['service_event_template'].widget = DataSelect(choices=choices, data=data)

        if self.instance and self.instance.unit_service_area_id:
            self.initial['unit'] = self.instance.unit_service_area.unit.name

    def clean_unit_service_area(self):
        return self._clean_readonly("unit_service_area")

    def clean_service_event_template(self):

        if self.instance:
            return self._clean_readonly("service_event_template")

        se_template = self.cleaned_data.get('service_event_template')
        usa = self.cleaned_data.get('unit_service_area')
        mismatched_service_area = (
            se_template and
            usa and
            se_template.service_area and
            usa.service_area != se_template.service_area
        )
        if mismatched_service_area:
            msg = "The template service area (%s) does not match the unit's service area (%s)" % (
                se_template.service_area,
                usa.service_area,
            )
            raise forms.ValidationError(msg)

        return se_template

    def _clean_readonly(self, f):

        data = self.cleaned_data.get(f)

        if self.instance.pk and f in self.changed_data:
            orig = getattr(self.instance, f)
            err_msg = _(
                "To prevent data loss, you can not change the Unit Service Area or Service Event Template "
                "of a ServiceEventSchedule after it has been created. The original value was: %(object_id)s"
            ) % {
                'object_id': orig
            }
            self.add_error(f, err_msg)

        return data


class ServiceEventScheduleAdmin(BaseQATrackAdmin):

    list_filter = [
        SEScheduleSiteFilter,
        SEScheduleUnitFilter,
        SEScheduleServiceTypeFilter,
        'frequency',
        q_admin.ActiveFilter,
    ]

    list_display = [
        'get_name',
        'get_site',
        'get_unit',
        'get_service_area',
        freq_name,
        assigned_to_name,
        "active"
    ]

    search_fields = [
        'service_event_template__name',
        "unit_service_area__unit__name",
        "unit_service_area__service_area__name",
        "frequency__name",
    ]
    list_editable = ["active"]

    filter_horizontal = ("visible_to",)

    save_as = True

    form = ServiceEventScheduleAdminForm

    class Media:
        js = (
            "admin/js/jquery.init.js",
            'jquery/js/jquery.min.js',
            "select2/js/select2.js",
            "js/serviceeventschedule_admin.js",
        )
        css = {
            'all': (
                "qatrack_core/css/admin.css",
                "select2/css/select2.css",
            ),
        }

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'service_event_template',
            'unit_service_area',
            'unit_service_area__unit',
            'unit_service_area__service_area',
            'frequency',
        )

    def get_name(self, ses):
        return ses.service_event_template.name
    get_name.short_description = _l('Template Name')
    get_name.admin_order_field = 'service_event_template__name'

    def get_site(self, ses):
        return ses.unit_service_area.unit.site.name if ses.unit_service_area.unit.site else _l("Other")
    get_site.short_description = _l('Site')
    get_site.admin_order_field = 'unit_service_area__unit__site'

    def get_unit(self, ses):
        return ses.unit_service_area.unit.name
    get_unit.short_description = _l('Unit')
    get_unit.admin_order_field = 'unit_service_area__unit'

    def get_service_area(self, ses):
        return ses.unit_service_area.service_area.name
    get_service_area.short_description = _l('Service Area')
    get_service_area.admin_order_field = 'unit_service_area__service_area.name'


class ServiceEventTemplateAdmin(SaveUserQATrackAdmin):

    list_filter = ['service_type']

    list_display = [
        'name',
        'service_area',
        'service_type',
        'is_review_required',
    ]
    search_fields = [
        'name',
        "service_area__name",
        "service_type__name",
        "problem_description",
        "work_description",
    ]
    filter_horizontal = ["return_to_service_test_lists"]

    save_as = True

    fieldsets = [
        (
            _l("Name"),
            {
                'fields': ['name'],
            },
        ),
        (
            _l("Service Event"),
            {
                'fields': [
                    'service_area',
                    'service_type',
                    'problem_description',
                    'work_description',
                    'is_review_required',
                ]
            },
        ),
        (
            _l("Return to Service"),
            {
                'fields': ['return_to_service_test_lists']
            },
        ),
    ]


admin.site.register(ServiceArea, ServiceAreaAdmin)
admin.site.register(ServiceEvent, ServiceEventAdmin)
admin.site.register(ServiceType, ServiceTypeAdmin)
admin.site.register(ServiceEventStatus, ServiceEventStatusAdmin)
admin.site.register(UnitServiceArea, UnitServiceAreaAdmin)
admin.site.register(GroupLinker, GroupLinkerAdmin)
admin.site.register(ServiceEventSchedule, ServiceEventScheduleAdmin)
admin.site.register(ServiceEventTemplate, ServiceEventTemplateAdmin)
admin.site.register([ThirdParty], BaseQATrackAdmin)
