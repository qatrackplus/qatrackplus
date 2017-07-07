
from braces.views import PermissionRequiredMixin
from django.conf import settings
from django.core.urlresolvers import reverse, resolve
from django.db.models import ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template import Context
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, CreateView

from listable.views import (
    BaseListableView, DATE_RANGE, SELECT, SELECT_MULTI, NONEORNULL, TEXT,
    TODAY, YESTERDAY, TOMORROW, LAST_WEEK, THIS_WEEK, NEXT_WEEK, LAST_14_DAYS, LAST_MONTH, THIS_MONTH, THIS_YEAR
)

from qatrack.units import models as u_models
from qatrack.units import forms
from qatrack.service_log import models as sl_models


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

    permission_required = "units.can_change_available_time"
    raise_exception = True
    template_name = 'units/unit_available_time_change.html'

    def get_context_data(self, **kwargs):
        context = super(UnitAvailableTimeChange, self).get_context_data(**kwargs)
        context['unit_availble_time_form'] = forms.UnitAvailableTimeForm()
        context['unit_availble_time_edit_form'] = forms.UnitAvailableTimeEditForm()
        return context


# class ServiceLogDownTimes(BaseListableView):
#
#     template_name = 'units/unit_down_time.html'
#     model =


class HandleUnitAvailableTimeChange(PermissionRequiredMixin, CreateView):

    permission_required = "units.can_change_available_time"
    raise_exception = True
    model = u_models.UnitAvailableTime
    form_class = forms.UnitAvailableTimeForm
    template_name = 'units/unit_available_time_change.html'

    def get_context_data(self, **kwargs):
        super(HandleUnitAvailableTimeChange, self).get_context_data(**kwargs)
        if self.request.method == 'POST':
            print('posting')
        else:
            print('not posting')

    def form_valid(self, form):
        print('forms valid')
        for u in form.cleaned_data['units']:
            date_changed = form.cleaned_data['date_changed']
            try:
                uat = u_models.UnitAvailableTime.objects.get(date_changed=date_changed, unit=u)

                uat.hours_monday = form.cleaned_data['hours_monday']
                uat.hours_tuesday = form.cleaned_data['hours_tuesday']
                uat.hours_wednesday = form.cleaned_data['hours_wednesday']
                uat.hours_thursday = form.cleaned_data['hours_thursday']
                uat.hours_friday = form.cleaned_data['hours_friday']
                uat.hours_saturday = form.cleaned_data['hours_saturday']
                uat.hours_sunday = form.cleaned_data['hours_sunday']
                uat.save()
                print('Changed existing uat for %s' % u.name)
            except ObjectDoesNotExist:
                u_models.UnitAvailableTime.objects.create(
                    date_changed=date_changed,
                    unit=u,
                    hours_monday=form.cleaned_data['hours_monday'],
                    hours_tuesday=form.cleaned_data['hours_tuesday'],
                    hours_wednesday=form.cleaned_data['hours_wednesday'],
                    hours_thursday=form.cleaned_data['hours_thursday'],
                    hours_friday=form.cleaned_data['hours_friday'],
                    hours_saturday=form.cleaned_data['hours_saturday'],
                    hours_sunday=form.cleaned_data['hours_sunday']
                )

        return JsonResponse({'message': 'Finsished'})

    def form_invalid(self, form):
        return JsonResponse({'errors': form.errors})


class HandleUnitAvailableTimeEditAdd(PermissionRequiredMixin, CreateView):

    permission_required = "units.can_change_available_time"
    raise_exception = True
    model = u_models.UnitAvailableTimeEdit
    form_class = forms.UnitAvailableTimeEditForm

    def form_valid(self, form):
        for u in form.cleaned_data['units']:
            date = form.cleaned_data['date']
            try:
                uate = u_models.UnitAvailableTimeEdit.objects.get(date=date, unit=u)
                uate.hours = form.cleaned_data['hours_monday']
                uate.name = form.cleaned_data['name']
                uate.save()
            except ObjectDoesNotExist:
                u_models.UnitAvailableTimeEdit.objects.create(
                    date=date,
                    unit=u,
                    hours=form.cleaned_data['hours'],
                    name=form.cleaned_data['name']
                )

        return JsonResponse({'message': 'Finsished'})

    def form_invalid(self, form):
        return JsonResponse({'errors': form.errors})


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
        c = Context({'se': se, 'request': self.request, 'next': mext})
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
        c = Context({'u': u, 'request': self.request, 'next': mext, 'USE_PARTS': settings.USE_PARTS})
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
