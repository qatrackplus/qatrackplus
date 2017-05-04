
from braces.views import LoginRequiredMixin
from django.core.urlresolvers import reverse, resolve
from django.db.models import Q
from django.forms.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from django.views.generic.edit import ModelFormMixin, ProcessFormView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic import TemplateView, DetailView

from listable.views import (
    BaseListableView, DATE_RANGE, SELECT_MULTI, NONEORNULL, TEXT, SELECT_MULTI_FROM_MULTI,
    TODAY, YESTERDAY, TOMORROW, LAST_WEEK, THIS_WEEK, NEXT_WEEK, LAST_14_DAYS, LAST_MONTH, THIS_MONTH, THIS_YEAR
)

from . import models as p_models
from . import forms as p_forms


def parts_searcher(request):
    p_search = request.GET['q']
    parts = p_models.Part.objects\
        .filter(Q(part_number__icontains=p_search) | Q(description__icontains=p_search)) \
        .order_by('part_number')[0:50]\
        .values_list('id', 'part_number', 'alt_part_number', 'description', 'quantity_current')
    return JsonResponse({'data': list(parts)}, safe=False)


def parts_storage_searcher(request):

    try:
        p_id = int(request.GET['p_id'])
    except ValueError:
        return JsonResponse({'data': '__clear__'}, safe=False)

    print(p_id)
    psc = p_models.PartStorageCollection.objects \
        .filter(part=p_id) \
        .select_related('storage', 'storage__room', 'storage__room__site') \
        .order_by('storage__room__site__name', 'storage__room__name', 'storage__location')[0:50] \
        .values_list('storage_id', 'storage__room__site__name', 'storage__room__name', 'storage__location', 'quantity')
    print(psc)
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
    # form_class = AuthorForm
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

    def form_valid(self, form):

        context = self.get_context_data()
        supplier_formset = context['supplier_formset']
        storage_formset = context['storage_formset']

        if not supplier_formset.is_valid() or not storage_formset.is_valid():
            return self.render_to_response(context)

        part = form.save()

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
            print('+++++++++++++++++++++++++++++++++')
            print(sto_form.changed_data)
            if delete and not is_new:
                psc_instance.delete()
                continue

            elif sto_form.has_changed():
                psc_instance.part = part
                storage_field = sto_form.cleaned_data['storage_field']
                print('+++++++++++++++++++++++++++++++++')
                print(storage_field)
                if storage_field[0]:
                    psc_instance.storage = p_models.Storage.objects.create(
                        room=sto_form.cleaned_data['room'],
                        location=storage_field[1]
                    )
                else:
                    psc_instance.storage = storage_field[1]

                psc_instance.save()
                part.set_quantity_current()

        return HttpResponseRedirect(reverse('parts_list'))


# class CreatePart(PartUpdateCreate):
#
#     def form_valid(self, form):
#         self.instance = form.save(commit=False)
#         form.instance.user_created_by = self.request.user
#         form.instance.datetime_created = timezone.now()
#
#         return super(CreatePart, self).form_valid(form)

# class UpdateServiceEvent(ServiceEventUpdateCreate):
# class DetailsServiceEvent(DetailView):

class PartsList(BaseListableView):
    model = p_models.Part
    template_name = 'service_log/service_event_list.html'
    paginate_by = 50

    # order_by = ['part_number']
    kwarg_filters = None
    multi_separator = '<span class="padding-0-10">|</span>'

    fields = (
        'actions',
        'pk',
        'description',
        'part_number',
        'quantity_current',
        'part_categories__name'
    )

    headers = {
        'actions': _('Actions'),
        'pk': _('ID'),
        'description': _('Description'),
        'part_number': _('Part Number'),
        'quantity_current': _('In Storage'),
        'part_categories__name': _('Categories')
    }

    widgets = {
        'actions': None,
        'pk': TEXT,
        'description': TEXT,
        'part_number': TEXT,
        'quantity_current': None,
        'part_categories__name': SELECT_MULTI_FROM_MULTI
    }

    search_fields = {
        'actions': False,
        'quantity_current': False
    }

    order_fields = {
        'actions': False,
        'part_categories__name': False
    }

    prefetch_related = (
        'part_categories',
    )

    def get_icon(self):
        return 'fa-cog'

    def get_page_title(self, f=None):
        if not f:
            return 'All Parts'

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
        context['page_title'] = self.get_page_title(f)
        return context

    def actions(self, p):
        template = get_template('parts/table_context_p_actions.html')
        mext = reverse('parts_list')
        c = Context({'p': p, 'request': self.request, 'next': mext})
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
        c = Context({'p': p, 'request': self.request, 'next': mext})
        return template.render(c)
