from collections import defaultdict

from braces.views import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.context_processors import PermWrapper
from django.db.models import Count, F, Q
from django.forms.utils import timezone
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.urls import resolve, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import DetailView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView
from listable.views import SELECT_MULTI, TEXT, BaseListableView

from qatrack.attachments.models import Attachment
from qatrack.attachments.views import listable_attachment_tags
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

        context_data['attachments'] = self.object.attachment_set.all() if self.object else []
        return context_data

    def form_invalid(self, form):
        messages.add_message(self.request, messages.ERROR, _('Please correct the errors below.'))
        return super().form_invalid(form)

    def edit_part_attachments(self, part):
        for idx, f in enumerate(self.request.FILES.getlist('part_attachments')):
            Attachment.objects.create(
                attachment=f,
                comment="Uploaded %s by %s" % (timezone.now(), self.request.user.username),
                label=f.name,
                part=part,
                created_by=self.request.user
            )

        a_ids = self.request.POST.get('part_attachments_delete_ids', '').split(',')
        if a_ids != ['']:
            Attachment.objects.filter(id__in=a_ids).delete()

    def form_valid(self, form):

        context = self.get_context_data()
        supplier_formset = context['supplier_formset']
        storage_formset = context['storage_formset']

        if not supplier_formset.is_valid() or not storage_formset.is_valid():
            messages.add_message(self.request, messages.ERROR, _('Please correct the errors below.'))
            return self.render_to_response(context)

        part = form.save(commit=False)
        if not part.pk:
            message = _('New part %(description)s added') % {'description': str(part)}
        else:
            message = _('Part %(description)s updated') % {'description': str(part)}

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

        self.edit_part_attachments(part)

        if 'submit_add_another' in self.request.POST:
            return HttpResponseRedirect(reverse('part_new'))
        return HttpResponseRedirect(reverse('parts_list'))


class PartDetails(DetailView):

    model = p_models.Part
    template_name = 'parts/part_details.html'


class PartsList(BaseListableView):

    page_title = _l("All Parts")
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
        'new_or_used',
        'quantity_current',
        'quantity_min',
        'part_category__name',
        'locations',
        'attachments',
    )

    headers = {
        'actions': _l('Actions'),
        'name': _l('Name'),
        'part_number': _l('Part Number'),
        'new_or_used': _l('New or Used'),
        'quantity_current': _l('In Storage'),
        'quantity_min': _l('Min Quantity'),
        'locations': _l("Locations"),
        'part_category__name': _l('Category'),
        "attachments": mark_safe('<i class="fa fa-paperclip fa-fw" aria-hidden="true"></i>'),
    }

    widgets = {
        'actions': None,
        'name': TEXT,
        'part_number': TEXT,
        'new_or_used': SELECT_MULTI,
        'quantity_min': None,
        'quantity_current': None,
        'locations': None,
        'part_category__name': SELECT_MULTI,
        'attachments': None,
    }

    search_fields = {
        'actions': False,
        'quantity_current': False,
        'quantity_min': False,
        'locations': False,
        'attachments': False,
    }

    order_fields = {
        'actions': False,
        'part_category__name': False,
        'locations': "partstoragecollection__storage__room__site__name",
        "attachments": "attachment_count",
    }

    select_related = ('part_category',)
    prefetch_related = ("attachment_set",)

    def get_icon(self):
        return 'fa-cog'

    def get(self, request, *args, **kwargs):
        if self.kwarg_filters is None:
            self.kwarg_filters = kwargs.pop('f', None)
        return super(PartsList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super(PartsList, self).get_queryset()
        return qs.annotate(attachment_count=Count("attachment"))

    def format_col(self, field, obj):
        col = super(PartsList, self).format_col(field, obj)
        return col

    def get_context_data(self, *args, **kwargs):
        context = super(PartsList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        context['page_title'] = self.page_title
        return context

    def actions(self, p):
        template = get_template('parts/table_context_p_actions.html')
        mext = reverse('parts_list')
        perms = PermWrapper(self.request.user)
        c = {'p': p, 'request': self.request, 'next': mext, 'perms': perms}
        return template.render(c)

    def locations(self, obj):
        return self.parts_locations_cache.get(obj.id, _("None in storage"))

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
            text = (
                '<div style="display: inline-block; white-space: nowrap;">'
                '%s%s:%s <span class="badge">%d</span>'
                '</div>'
            ) % (site, room_name, loc or "", quantity)
            tmp_cache[part_id].append(text)

        self._parts_locations_cache = {}
        for k, v in tmp_cache.items():
            self._parts_locations_cache[k] = ', '.join(v)

    def part_number(self, part):
        return part.part_number or "<em>N/A</em>"

    def attachments(self, part):
        return listable_attachment_tags(part)


class LowInventoryPartsList(PartsList):

    page_title = _l("Low Inventory Parts")

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(quantity_current__lt=F('quantity_min'))


class SuppliersList(BaseListableView):

    model = p_models.Supplier
    template_name = 'service_log/service_event_list.html'
    paginate_by = 50

    # order_by = ['part_number']
    kwarg_filters = None

    fields = (
        'actions',
        'name',
        'phone_number',
        'get_website_tag',
    )

    headers = {
        'actions': _l('Actions'),
        'name': _l('Name'),
        'phone_number': _l("Phone Number"),
        'get_website_tag': _l("Website"),
    }

    widgets = {
        'actions': None,
        'name': TEXT,
        'phone_number': TEXT,
        'website': TEXT,
    }

    search_fields = {
        'actions': False,
        'get_website_tag': 'website',
    }

    order_fields = {
        'actions': False,
        'get_website_tag': 'website',
    }

    def get_context_data(self, *args, **kwargs):
        context = super(SuppliersList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = 'fa-microchip'
        context['page_title'] = _l("All Suppliers")
        return context

    def actions(self, supplier):
        template = get_template('parts/table_context_suppliers_actions.html')
        mext = reverse('suppliers_list')
        c = {
            'supplier': supplier,
            'request': self.request,
            'next': mext,
            'perms': PermWrapper(self.request.user),
        }
        return template.render(c)


class SupplierDetails(PartsList):

    template_name = 'parts/supplier_details.html'

    def get_queryset(self):
        return super().get_queryset().filter(partsuppliercollection__supplier__id=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['supplier'] = get_object_or_404(p_models.Supplier, pk=self.kwargs['pk'])
        return context
