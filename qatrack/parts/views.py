
import csv

from braces.views import LoginRequiredMixin
from decimal import Decimal
from django.urls import reverse, resolve
from django.contrib.auth.context_processors import PermWrapper
from django.contrib import messages
from django.db.models import F, Q, Sum
from django.forms.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.views.generic.edit import ModelFormMixin, ProcessFormView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic import TemplateView, DetailView
from io import BytesIO
from reportlab.pdfgen import canvas

from listable.views import (
    BaseListableView,
    SELECT_MULTI,
    NONEORNULL,
    TEXT,
)

from . import models as p_models
from . import forms as p_forms
from qatrack.units import models as u_models
from qatrack.service_log import models as s_models


def parts_searcher(request):
    p_search = request.GET['q']
    parts = p_models.Part.objects\
        .filter(Q(part_number__icontains=p_search) | Q(name__icontains=p_search)) \
        .order_by('part_number')[0:50]\
        .values_list('id', 'part_number', 'alt_part_number', 'name', 'quantity_current')
    return JsonResponse({'data': list(parts)}, safe=False)


def parts_storage_searcher(request):

    try:
        p_id = int(request.GET['p_id'])
    except ValueError:
        return JsonResponse({'data': '__clear__'}, safe=False)

    psc = p_models.PartStorageCollection.objects \
        .filter(part=p_id) \
        .select_related('storage', 'storage__room', 'storage__room__site') \
        .order_by('storage__room__site__name', 'storage__room__name', 'storage__location')[0:50] \
        .values_list('storage_id', 'storage__room__site__name', 'storage__room__name', 'storage__location', 'quantity')

    return JsonResponse({'data': list(psc)}, safe=False)


def room_location_searcher(request):

    try:
        r_id = int(request.GET['r_id'])
    except ValueError:
        return JsonResponse({'data': '__clear__'}, safe=False)

    storage = p_models.Storage.objects \
        .filter(room=r_id, location__isnull=False) \
        .select_related('room', 'room__site') \
        .order_by('room__site__name', 'room__name', 'location') \
        .values_list('id', 'location', 'description')

    storage_no_location, _ = p_models.Storage.objects \
        .get_or_create(room=p_models.Room.objects.get(pk=r_id), location__isnull=True)

    return JsonResponse({'storage': list(storage), 'storage_no_location': storage_no_location.id}, safe=False)


class PartUpdateCreate(LoginRequiredMixin, SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):

    model = p_models.Part
    template_name = 'parts/part_update.html'
    form_class = p_forms.PartForm

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super(PartUpdateCreate, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        try:
            return super(PartUpdateCreate, self).get_object(queryset)
        except AttributeError:
            return None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(PartUpdateCreate, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(PartUpdateCreate, self).post(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context_data = super(PartUpdateCreate, self).get_context_data(**kwargs)

        if self.request.method == 'POST':

            context_data['supplier_formset'] = p_forms.PartSupplierCollectionFormset(
                self.request.POST,
                instance=self.object,
                prefix='supplier'
            )
            context_data['storage_formset'] = p_forms.PartStorageCollectionFormset(
                self.request.POST,
                instance=self.object,
                prefix='storage'
            )
        else:
            context_data['supplier_formset'] = p_forms.PartSupplierCollectionFormset(instance=self.object, prefix='supplier')
            context_data['storage_formset'] = p_forms.PartStorageCollectionFormset(instance=self.object, prefix='storage')

        return context_data

    def form_invalid(self, form):
        messages.add_message(self.request, messages.ERROR, _('Please correct the errors below.'))
        return super().form_invalid(form)

    def form_valid(self, form):

        context = self.get_context_data()
        supplier_formset = context['supplier_formset']
        storage_formset = context['storage_formset']

        if not supplier_formset.is_valid() or not storage_formset.is_valid():
            messages.add_message(self.request, messages.ERROR, _('Please correct the errors below.'))
            return self.render_to_response(context)

        part = form.save(commit=False)
        message = 'New part %s added' % part.part_number if not part.pk else 'Part %s updated' % part.part_number
        messages.add_message(request=self.request, level=messages.SUCCESS, message=message)
        part.save()

        for sup_form in supplier_formset:

            delete = sup_form.cleaned_data.get('DELETE')
            is_new = sup_form.instance.id is None

            psc_instance = sup_form.instance

            if delete and not is_new:
                psc_instance.delete()
                continue

            elif sup_form.has_changed():
                psc_instance.part = part
                psc_instance.save()

        for sto_form in storage_formset:

            delete = sto_form.cleaned_data.get('DELETE')
            is_new = sto_form.instance.id is None

            psc_instance = sto_form.instance
            if delete and not is_new:
                psc_instance.delete()
                continue

            elif sto_form.has_changed():
                psc_instance.part = part
                storage_field = sto_form.cleaned_data['storage_field']

                if isinstance(storage_field, str):
                    psc_instance.storage = p_models.Storage.objects.create(
                        room=sto_form.cleaned_data['room'],
                        location=storage_field
                    )
                else:
                    psc_instance.storage = storage_field

                psc_instance.save()
                part.set_quantity_current()

        if 'submit_add_another' in self.request.POST:
            return HttpResponseRedirect(reverse('part_new'))
        return HttpResponseRedirect(reverse('parts_list'))


class PartDetails(DetailView):

    model = p_models.Part
    template_name = 'parts/part_details.html'


class PartsList(BaseListableView):
    model = p_models.Part
    template_name = 'parts/parts_list.html'
    paginate_by = 50

    # order_by = ['part_number']
    kwarg_filters = None
    multi_separator = '<span class="padding-0-10">|</span>'

    fields = (
        'actions',
        'name',
        'part_number',
        'quantity_current',
        'quantity_min',
        'part_category__name'
    )

    headers = {
        'actions': _('Actions'),
        'name': _('Name'),
        'part_number': _('Part Number'),
        'quantity_min': _('Min Quantity'),
        'quantity_current': _('In Storage'),
        'part_category__name': _('Category')
    }

    widgets = {
        'actions': None,
        'name': TEXT,
        'part_number': TEXT,
        'quantity_min': None,
        'quantity_current': None,
        'part_category__name': SELECT_MULTI
    }

    search_fields = {
        'actions': False,
        'quantity_current': False,
        'quantity_min': False
    }

    order_fields = {
        'actions': False,
        'part_category__name': False
    }

    select_related = ('part_category',)

    def get_icon(self):
        return 'fa-cog'

    def get_page_title(self, f=None):
        if not f:
            return 'All Parts'
        to_return = 'Parts'
        filters = f.split('_')
        for filt in filters:
            [key, val] = filt.split('-')
            if key == 'qcqm':
                if val == 'lt':
                    to_return += ' - Low Inventory'

        return to_return

    def get(self, request, *args, **kwargs):
        if self.kwarg_filters is None:
            self.kwarg_filters = kwargs.pop('f', None)
        return super(PartsList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super(PartsList, self).get_queryset()

        if self.kwarg_filters is None:
            self.kwarg_filters = self.request.GET.get('f', None)

        if self.kwarg_filters is not None:
            filters = self.kwarg_filters.split('_')
            query_kwargs = {}
            for filt in filters:
                [key, val] = filt.split('-')
                if key == 'qcqm':
                    if val == 'lt':
                        qs = qs.filter(quantity_current__lt=F('quantity_min'))

            qs = qs.filter(**query_kwargs)

        return qs

    def format_col(self, field, obj):
        col = super(PartsList, self).format_col(field, obj)
        return col

    def get_context_data(self, *args, **kwargs):
        context = super(PartsList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        f = self.request.GET.get('f', False)
        context['kwargs'] = {'f': f} if f else {}
        if f == 'qcqm-lt':
            context['print_parts'] = True
        context['page_title'] = self.get_page_title(f)
        return context

    def actions(self, p):
        template = get_template('parts/table_context_p_actions.html')
        mext = reverse('parts_list')
        perms = PermWrapper(self.request.user)
        c = {'p': p, 'request': self.request, 'next': mext, 'perms': perms}
        return template.render(c)


class SuppliersList(BaseListableView):

    model = p_models.Supplier
    template_name = 'service_log/service_event_list.html'
    paginate_by = 50

    # order_by = ['part_number']
    kwarg_filters = None

    fields = (
        'actions',
        'pk',
        'name',
        'notes'
    )

    headers = {
        'actions': _('Actions'),
        'pk': _('ID'),
        'name': _('Name'),
        'notes': _('Notes'),
    }

    widgets = {
        'actions': None,
        'pk': TEXT,
        'name': TEXT,
        'notes': TEXT,
    }

    search_fields = {
        'actions': False,
    }

    order_fields = {
        'actions': False,
        'notes': False
    }

    def get_icon(self):
        return 'fa-microchip'

    def get_page_title(self, f=None):
        if not f:
            return 'All Suppliers'

    def format_col(self, field, obj):
        col = super(SuppliersList, self).format_col(field, obj)
        return col

    def get_context_data(self, *args, **kwargs):
        context = super(SuppliersList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        f = self.request.GET.get('f', False)
        context['kwargs'] = {'f': f} if f else {}
        context['page_title'] = self.get_page_title(f)
        return context

    def actions(self, p):
        template = get_template('parts/table_context_suppliers_actions.html')
        mext = reverse('parts_list')
        c = {'p': p, 'request': self.request, 'next': mext}
        return template.render(c)

