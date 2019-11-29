from collections import defaultdict

from braces.views import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.context_processors import PermWrapper
from django.db.models import F, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.urls import resolve, reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import DetailView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView
from listable.views import SELECT_MULTI, TEXT, BaseListableView

from qatrack.parts import forms as p_forms
from qatrack.parts import models as p_models


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
            context_data['supplier_formset'] = p_forms.PartSupplierCollectionFormset(instance=self.object, prefix='supplier')  # noqa: E501
            context_data['storage_formset'] = p_forms.PartStorageCollectionFormset(instance=self.object, prefix='storage')  # noqa: E501

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
        if not part.pk:
            message = _('New part %(part_number)s added') % {'part_number': part.part_number}
        else:
            message = _('Part %(part_number)s updated') % {'part_number': part.part_number}

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
        'locations',
        'part_category__name',
    )

    headers = {
        'actions': _l('Actions'),
        'name': _l('Name'),
        'part_number': _l('Part Number'),
        'quantity_current': _l('In Storage'),
        'quantity_min': _l('Min Quantity'),
        'locations': _l("Locations"),
        'part_category__name': _l('Category'),
    }

    widgets = {
        'actions': None,
        'name': TEXT,
        'part_number': TEXT,
        'quantity_min': None,
        'quantity_current': None,
        'locations': None,
        'part_category__name': SELECT_MULTI,
    }

    search_fields = {
        'actions': False,
        'quantity_current': False,
        'quantity_min': False,
        'locations': False,
    }

    order_fields = {
        'actions': False,
        'part_category__name': False,
        'locations': "partstoragecollection__storage__room__site__name",
    }

    select_related = ('part_category',)

    def get_icon(self):
        return 'fa-cog'

    def get_page_title(self, f=None):
        if not f:
            return _l("All Parts")
        to_return = _l("Parts")
        filters = f.split('_')
        for filt in filters:
            [key, val] = filt.split('-')
            if key == 'qcqm':
                if val == 'lt':
                    to_return += ' - ' + _("Low Inventory")

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

    def locations(self, obj):
        return self.parts_locations_cache[obj.id]

    @property
    def parts_locations_cache(self):
        if not hasattr(self, "_parts_locations_cache"):
            self._generate_parts_locations()
        return self._parts_locations_cache

    def _generate_parts_locations(self):

        psc = p_models.PartStorageCollection.objects.order_by(
            "storage__room__site__name",
            "storage__room__name",
            "storage__location",
        ).values_list(
            "part_id",
            "quantity",
            "storage__location",
            "storage__room__site__name",
            "storage__room__name",
        )

        tmp_cache = defaultdict(list)
        for part_id, quantity, loc, site_name, room_name in psc:
            site = "%s:" % site_name if site_name else ""
            text = '<div style="display: inline-block; white-space: nowrap;">%s%s:%s <span class="badge">%d</span></div>' % (
                site, room_name, loc or "", quantity
            )
            tmp_cache[part_id].append(text)

        self._parts_locations_cache = {}
        for k, v in tmp_cache.items():
            self._parts_locations_cache[k] = ', '.join(v)


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
        'actions': _l('Actions'),
        'pk': _l('ID'),
        'name': _l('Name'),
        'notes': _l('Notes'),
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
            return _l("All Suppliers")

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
