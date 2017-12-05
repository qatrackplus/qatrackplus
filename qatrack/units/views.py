
import json

from braces.views import PermissionRequiredMixin
from django.conf import settings
from django.core.urlresolvers import reverse, resolve
from django.utils import timezone
from django.db.models import ObjectDoesNotExist
from django.http import JsonResponse
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, CreateView

from listable.views import (
    BaseListableView,
    SELECT,
    SELECT_MULTI,
    NONEORNULL,
    TEXT,
)

from qatrack.units import models as u_models
from qatrack.units import forms


def get_unit_available_time_data(request):

    unit_qs = u_models.Unit.objects.prefetch_related('unitavailabletime_set', 'unitavailabletimeedit_set').all()
    unit_available_time_data = {u.id: {
        'number': u.number,
        'name': u.name,
        'active': u.active,
        'available_time_edits': {
            uate.date.strftime('%Y-%m-%d'): {
                'name': uate.name,
                'hours': uate.hours
            } for uate in u.unitavailabletimeedit_set.all()
        },
        'available_times': list(u.unitavailabletime_set.all().values())
    } for u in unit_qs}

    return JsonResponse({'unit_available_time_data': unit_available_time_data})


class UnitsFromKwargs(TemplateView):

    queryset = u_models.Unit.objects.none()

    def get(self, request, *args, **kwargs):

        filters = request.GET
        self.queryset = self.get_queryset(filters, pk=kwargs.get('pk', None))
        return super().get(request, *args, **kwargs)

    def get_queryset(self, filters, pk=None):
        """K, I guess this works :/ """

        if pk is None:
            qs = u_models.Unit.objects.prefetch_related('service_areas').all()
            for filt in filters:
                if filt in ['site', 'type', 'type__vendor', 'type__unit_class']:
                    filt_multi = filters[filt].split(',')
                    if NONEORNULL in filt_multi:
                        qs = qs.filter(**{'%s__name__in' % filt: filt_multi}) | qs.filter(**{filt: None})
                    else:
                        qs = qs.filter(**{'%s__name__in' % filt: filt_multi})
                elif filt in ['active', 'restricted']:
                    qs = qs.filter(**{filt: filters[filt]})
                else:
                    qs = qs.filter(**{'%s__icontains' % filt: filters[filt]})
        else:
            qs = u_models.Unit.objects.filter(pk=pk)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = self.queryset
        return context


class UnitAvailableTimeChange(PermissionRequiredMixin, UnitsFromKwargs):

    permission_required = 'units.change_unitavailabletime'
    raise_exception = True
    template_name = 'units/unit_available_time_change.html'

    def get_context_data(self, **kwargs):
        context = super(UnitAvailableTimeChange, self).get_context_data(**kwargs)
        context['unit_availble_time_form'] = forms.UnitAvailableTimeForm()
        context['unit_availble_time_edit_form'] = forms.UnitAvailableTimeEditForm()
        return context


def handle_unit_available_time(request):

    day = timezone.datetime.fromtimestamp(int(request.POST.get('day'))/1000, timezone.utc).date()
    hours = {'monday': ['0', '0'], 'tuesday': ['0', '0'], 'wednesday': ['0', '0'], 'thursday': ['0', '0'], 'friday': ['0', '0'], 'saturday': ['0', '0'], 'sunday': ['0', '0']}
    for d in hours:
        hours_min = request.POST.get('hours_' + d).replace('_', '0')
        if hours_min != '':
            hours_min = hours_min.split(':')
            hours[d] = hours_min
    units = [u_models.Unit.objects.get(id=u_id) for u_id in request.POST.getlist('units[]', [])]

    for u in units:
        try:
            uat = u_models.UnitAvailableTime.objects.get(unit=u, date_changed=day)
            for d in hours:
                setattr(uat, 'hours_' + d, timezone.timedelta(hours=int(hours[d][0]), minutes=int(hours[d][1])))
            uat.save()
        except ObjectDoesNotExist:
            uat = u_models.UnitAvailableTime.objects.create(
                unit=u,
                date_changed=day,
                hours_monday=timezone.timedelta(hours=int(hours['monday'][0]), minutes=int(hours['monday'][1])),
                hours_tuesday=timezone.timedelta(hours=int(hours['tuesday'][0]), minutes=int(hours['tuesday'][1])),
                hours_wednesday=timezone.timedelta(hours=int(hours['wednesday'][0]), minutes=int(hours['wednesday'][1])),
                hours_thursday=timezone.timedelta(hours=int(hours['thursday'][0]), minutes=int(hours['thursday'][1])),
                hours_friday=timezone.timedelta(hours=int(hours['friday'][0]), minutes=int(hours['friday'][1])),
                hours_saturday=timezone.timedelta(hours=int(hours['saturday'][0]), minutes=int(hours['saturday'][1])),
                hours_sunday=timezone.timedelta(hours=int(hours['sunday'][0]), minutes=int(hours['sunday'][1])),
            )

    return get_unit_available_time_data(request)


def handle_unit_available_time_edit(request):

    hours_mins = request.POST.get('hours_mins', None)
    if hours_mins:
        hours_mins = hours_mins.replace('_', '0').split(':')
        hours = int(hours_mins[0])
        mins = int(hours_mins[1])
        units = [u_models.Unit.objects.get(id=u_id) for u_id in request.POST.getlist('units[]', [])]
        days = [timezone.datetime.fromtimestamp(int(d)/1000, timezone.utc).date() for d in request.POST.getlist('days[]', [])]
        name = request.POST.get('name', None)

        for d in days:
            for u in units:
                try:
                    uate = u_models.UnitAvailableTimeEdit.objects.get(unit=u, date=d)
                    uate.hours = timezone.timedelta(hours=hours, minutes=mins)
                    uate.name = name
                    uate.save()
                except ObjectDoesNotExist:
                    uate = u_models.UnitAvailableTimeEdit.objects.create(
                        unit=u, date=d, hours=timezone.timedelta(hours=hours, minutes=mins), name=name
                    )

    return get_unit_available_time_data(request)


class VendorsList(BaseListableView):
    """
        This view provides a base for any sort of listing of
        :model:`units.Vendor`'s.
        """

    model = u_models.Vendor
    template_name = 'units/vendors_list.html'
    paginate_by = 50

    # order_by = ['-datetime_service']
    kwarg_filters = None

    fields = (
        'actions',
        'pk',
        'name',
        'notes',
        'thirdparties',
    )

    headers = {
        'pk': _('ID'),
        'thirdparties': _('Third Parties'),
    }

    widgets = {
        'actions': False,
        'pk': TEXT,
        'name': TEXT,
        'notes': TEXT,
        'thirdparties': False,
    }

    search_fields = {
        'actions': False,
        'thirdparties': False,
    }

    order_fields = {
        'actions': False,
        'thirdparties': False,
    }

    prefetch_related = (
        'thirdparty_set',
    )

    def __init__(self, *args, **kwargs):

        super(VendorsList, self).__init__(*args, **kwargs)
        self.templates = {
            'actions': get_template('units/table_context_v_actions.html'),
        }

    def get_icon(self):
        return 'fa-truck'

    def get_page_title(self, f=None):
        return 'Vendors'

    def get(self, request, *args, **kwargs):
        if self.kwarg_filters is None:
            self.kwarg_filters = kwargs.pop('f', None)
        return super(VendorsList, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(VendorsList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        f = self.request.GET.get('f', False)
        context['kwargs'] = {'f': f} if f else {}
        context['page_title'] = self.get_page_title(f)
        return context

    # def get_queryset(self):
    #     qs = super(VendorsList, self).get_queryset()
    #
    #     if self.kwarg_filters is None:
    #         self.kwarg_filters = self.request.GET.get('f', None)
    #
    #     if self.kwarg_filters is not None:
    #         filters = self.kwarg_filters.split('_')
    #         for filt in filters:
    #             [key, val] = filt.split('-')
    #             if key == 'ss':
    #                 qs = qs.filter(service_status=val)
    #             elif key == 'ar':
    #                 qs = qs.filter(is_approval_required=bool(int(val)))
    #             elif key == 'ss.ar':
    #                 qs = qs.filter(service_status__is_approval_required=bool(int(val)))
    #             elif key == 'u':
    #                 qs = qs.filter(unit_service_area__unit_id=val)
    #
    #     return qs

    def actions(self, se):
        template = self.templates['actions']
        mext = reverse('sl_list_all') + (('?f=' + self.kwarg_filters) if self.kwarg_filters else '')
        c = {'se': se, 'request': self.request, 'next': mext}
        return template.render(c)

    def thirdparties(self, v):
        names = []
        for tp in v.thirdparty_set.all():
            names.append('%s %s' % (tp.first_name, tp.last_name))
        return '<span class="padding-0-10">|</span>'.join(names)


class UnitList(BaseListableView):
    """
    This view provides a base for any sort of listing of
    :model:`units.Unit`'s.
    """

    model = u_models.Unit
    template_name = 'units/units_list.html'
    paginate_by = 50

    order_by = ['number']
    kwarg_filters = None

    fields = (
        'actions',
        'number',
        'name',
        'serial_number',
        'active',
        # 'restricted',
        'site__name',
        'type__unit_class__name',
        'type__name',
        'type__vendor__name',
        # 'modalities',
    )

    headers = {
        'site__name': _('Site'),
        'type__unit_class__name': _('Class'),
        'type__name': _('Type'),
        'type__vendor__name': _('Vendor')
    }

    widgets = {
        'actions': False,
        'number': TEXT,
        'name': TEXT,
        'serial_number': TEXT,
        'active': SELECT,
        # 'restricted': SELECT,
        'site__name': SELECT_MULTI,
        'type__unit_class__name': SELECT_MULTI,
        'type__name': SELECT_MULTI,
        'type__vendor__name': SELECT_MULTI,
        # 'modalities': False,
    }

    search_fields = {
        'actions': False,
        # 'modalities': False,
    }

    order_fields = {
        'actions': False,
        # 'modalities': False,
    }

    select_related = (
        'type',
        'type__unit_class',
        'type__vendor',
        'site'
    )

    # prefetch_related = (
    #     # 'modalities',
    # )

    def __init__(self, *args, **kwargs):

        super(UnitList, self).__init__(*args, **kwargs)
        self.templates = {
            'actions': get_template('units/table_context_u_actions.html'),
        }

    def get_icon(self):
        return 'fa-cubes'

    def get_page_title(self, f=None):
        return 'Units'

    def get(self, request, *args, **kwargs):
        if self.kwarg_filters is None:
            self.kwarg_filters = kwargs.pop('f', None)
        return super(UnitList, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(UnitList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        f = self.request.GET.get('f', False)
        context['kwargs'] = {'f': f} if f else {}
        context['page_title'] = self.get_page_title(f)
        return context

    def actions(self, u):
        template = self.templates['actions']
        mext = reverse('sl_list_all') + (('?f=' + self.kwarg_filters) if self.kwarg_filters else '')
        c = {'u': u, 'request': self.request, 'next': mext, 'USE_PARTS': settings.USE_PARTS}
        return template.render(c)

    def modalities(self, u):
        return ', '.join([m.name if m.name else '' for m in u.modalities.all()])


# def go_unit_down_time(request):
#
#     print(request.GET)
#
#     daterange = request.GET.get('date_range')
#     date_from = timezone.datetime.strptime(daterange.split(' - ')[0], '%d %b %Y')
#     date_to = timezone.datetime.strptime(daterange.split(' - ')[1], '%d %b %Y')
#
#     se_qs = sl_models.ServiceEvent.objects.filter(
#         datetime_service__gte=date_from, datetime_service__lte=date_to, duration_lost_time__isnull=False
#     )
#
#     units = None
#     print([se.id for se in se_qs])
#     return JsonResponse({'success': True, 'data': {'units': units}})
