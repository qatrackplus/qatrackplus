
from collections import OrderedDict
from braces.views import LoginRequiredMixin
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse, resolve
from django.db.models import Q
from django.forms.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, DetailView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView

from listable.views import (
    BaseListableView, DATE_RANGE, SELECT, SELECT_MULTI, NONEORNULL, TEXT,
    TODAY, YESTERDAY, TOMORROW, LAST_WEEK, THIS_WEEK, NEXT_WEEK, LAST_14_DAYS, LAST_MONTH, THIS_MONTH, THIS_YEAR
)

from qatrack.units import models as u_models


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
        'restricted',
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
        'restricted': SELECT,
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
        return 'fa-cube'

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

    def modalities(self, u):
        return ', '.join([m.name if m.name else '' for m in u.modalities.all()])
