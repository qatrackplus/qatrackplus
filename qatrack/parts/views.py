
import csv

from braces.views import LoginRequiredMixin
from decimal import Decimal
from django.core.urlresolvers import reverse, resolve
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
        .filter(Q(part_number__icontains=p_search) | Q(description__icontains=p_search)) \
        .order_by('part_number')[0:50]\
        .values_list('id', 'part_number', 'alt_part_number', 'description', 'quantity_current')
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


def go_units_parts_cost(request):

    daterange = request.GET.get('date_range')
    units = request.GET.getlist('units')
    service_areas = request.GET.getlist('service_areas')
    service_types = request.GET.getlist('service_types')

    date_from = timezone.datetime.strptime(daterange.split(' - ')[0], '%d %b %Y')
    date_to = timezone.datetime.strptime(daterange.split(' - ')[1], '%d %b %Y')

    qs_pu = p_models.PartUsed.objects.select_related(
        'service_event',
        'service_event__unit_service_area',
        'service_event__unit_service_area__unit',
        'service_event__unit_service_area__service_area',
        'service_event__service_type',
        'part'
    ).filter(
        service_event__datetime_service__gte=date_from,
        service_event__datetime_service__lte=date_to,
        service_event__unit_service_area__unit_id__in=units,
        service_event__unit_service_area__service_area_id__in=service_areas,
        service_event__service_type_id__in=service_types
    )

    total_parts_cost = qs_pu.aggregate(total_parts_cost=Sum('part__cost'))['total_parts_cost']

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="qatrack_parts_units_cost.csv"'
    response['Content-Type'] = 'text/csv; charset=utf-8'

    writer = csv.writer(response)
    headers = [
        ['Parts Cost for Units:', '', date_from.strftime('%d %b %Y'), ' to ', date_to.strftime('%d %b %Y')],
        ['Total Parts Cost: ', '', float(total_parts_cost) if total_parts_cost else 0],
        ['Service Types:', ''] + [st.name for st in s_models.ServiceType.objects.filter(pk__in=service_types)],
        [''],
        ['', 'Service Areas'],
        ['Units', ''] + [u.name for u in u_models.Unit.objects.filter(pk__in=units)] + ['Totals'],
    ]

    for sa in s_models.ServiceArea.objects.filter(pk__in=service_areas):
        row = ['', sa.name]
        for u in u_models.Unit.objects.filter(pk__in=units):
            try:
                usa = s_models.UnitServiceArea.objects.get(unit=u, service_area=sa)
                row.append(qs_pu.filter(service_event__unit_service_area=usa).aggregate(parts_cost=Sum('part__cost'))['parts_cost'] or 0)
            except s_models.UnitServiceArea.DoesNotExist:
                row.append('---')
        row.append(sum([r for r in row if type(r) in [int, Decimal]]))
        headers.append(row)

    headers.append(
        ['', 'Totals'] +
        [
            qs_pu.filter(
                service_event__unit_service_area__unit=u
            ).aggregate(
                parts_cost=Sum('part__cost')
            )['parts_cost'] or 0 for u in u_models.Unit.objects.filter(pk__in=units)
        ]
    )

    for h in headers:
        writer.writerow(h)

    return response


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

        part = form.save(commit=False)
        if not part.pk:
            messages.add_message(request=self.request, level=messages.SUCCESS, message='New part %s added' % part.part_number)
        else:
            messages.add_message(request=self.request, level=messages.SUCCESS, message='Part %s updated' % part.part_number)
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


class PartDetails(DetailView):

    model = p_models.Part
    template_name = 'parts/part_details.html'


class PartsUnitsCost(TemplateView):
    template_name = 'parts/parts_units_cost.html'
    queryset = u_models.Unit.objects.none()

    def get(self, request, *args, **kwargs):

        filters = request.GET
        self.queryset = self.get_queryset(filters, pk=kwargs.get('pk', None))
        return super(PartsUnitsCost, self).get(request, *args, **kwargs)

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
                # elif filt == 'klass':
                #     filt_multi = filters[filt].split(',')
                #     if NONEORNULL in filt_multi:
                #         qs = qs.filter(class__name__in=filt_multi) | qs.filter(**{filt: None})
                #     else:
                #         qs = qs.filter(class__name__in=filt_multi)
                elif filt in ['active', 'restricted']:
                    qs = qs.filter(**{filt: filters[filt]})
                else:
                    qs = qs.filter(**{'%s__icontains' % filt: filters[filt]})
        else:
            qs = u_models.Unit.objects.filter(pk=pk)

        return qs

    def get_context_data(self, **kwargs):
        context = super(PartsUnitsCost, self).get_context_data(**kwargs)
        context['names'] = [q.name for q in self.queryset]
        context['units'] = self.queryset.exclude(service_areas=None)
        context['service_areas'] = self.get_service_areas(self.queryset)
        context['service_types'] = self.get_service_types()
        return context

    def get_service_areas(self, queryset):
        sas = set()
        for u in queryset:
            sas.update(u.service_areas.all())
        return sas

    def get_service_types(self):
        return s_models.ServiceType.objects.all()

    def dispatch(self, request, *args, **kwargs):
        if s_models.ServiceType.objects.all().exists() and u_models.Unit.objects.all().exists() and s_models.ServiceArea.objects.all().exists():
            return super().dispatch(request, *args, **kwargs)
        return redirect(reverse('err'))


class PartsList(BaseListableView):
    model = p_models.Part
    template_name = 'parts/parts_list.html'
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
        'quantity_min',
        'part_category__name'
    )

    headers = {
        'actions': _('Actions'),
        'pk': _('ID'),
        'description': _('Description'),
        'part_number': _('Part Number'),
        'quantity_min': _('Min Quantity'),
        'quantity_current': _('In Storage'),
        'part_category__name': _('Category')
    }

    widgets = {
        'actions': None,
        'pk': TEXT,
        'description': TEXT,
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


def low_parts_pdf(request):

    low_parts_qs = p_models.Part.objects.filter(quantity_current__lt=F('quantity_min')).prefetch_related('suppliers')
    response = HttpResponse(content_type='application/pdf')
    date = timezone.now().strftime('%Y-%m-%d')
    filename = 'low-parts_%s' % date
    response['Content-Disposition'] = 'attachement; filename={0}.pdf'.format(filename)
    buffer = BytesIO()
    report = canvas.Canvas(buffer, bottomup=False)

    report.setFont('Helvetica-Bold', 10)

    report.drawString(80, 40, 'Low Parts (%s)' % date)

    report.drawString(30, 80, 'ID')
    report.drawString(70, 80, 'Description')
    report.drawString(270, 80, 'Part Number')
    report.drawString(360, 80, 'Quantity')
    report.drawString(420, 80, 'Suppliers')

    report.setFont('Helvetica', 8)
    page = 1
    report.drawString(500, 40, 'Page %s' % page)
    count = 1
    for lp in low_parts_qs:
        report.drawString(30, count * 10 + 90, str(lp.id))
        report.drawString(70, count * 10 + 90, str(lp.description))
        report.drawString(270, count * 10 + 90, str(lp.part_number))
        report.drawString(360, count * 10 + 90, str(lp.quantity_current))
        report.drawString(420, count * 10 + 90, str(' | '.join([s.name for s in lp.suppliers.all()])))
        count += 1
        if count > 70:

            page += 1
            report.showPage()
            report.setFont('Helvetica-Bold', 10)
            report.drawString(30, 80, 'ID')
            report.drawString(70, 80, 'Description')
            report.drawString(270, 80, 'Part Number')
            report.drawString(360, 80, 'Quantity')
            report.drawString(420, 80, 'Suppliers')
            report.setFont('Helvetica', 8)
            report.drawString(500, 40, 'Page %s' % page)
            count = 1

    report.showPage()
    report.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
