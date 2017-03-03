
from braces.views import LoginRequiredMixin
from django.core.urlresolvers import reverse, resolve
from django.db.models import Q
from django.forms.utils import timezone
from django.http import JsonResponse
from django.template import Context
from django.utils.translation import ugettext as _
from django.views.generic.edit import ModelFormMixin, ProcessFormView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic import TemplateView, DetailView

from listable.views import (
    BaseListableView, DATE_RANGE, SELECT_MULTI, NONEORNULL, TEXT,
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

    psc = p_models.PartStorageCollection.objects \
        .filter(part=p_id, storage__isnull=False) \
        .select_related('storage', 'storage__room', 'storage__room__site') \
        .order_by('storage__room__site__name', 'storage__room__name', 'storage__location')[0:50] \
        .values_list('storage_id', 'storage__room__site__name', 'storage__room__name', 'storage__location', 'quantity')

    return JsonResponse({'data': list(psc)}, safe=False)


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

            context_data['supplier_formset'] = p_forms.SupplierFormset(
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
            context_data['supplier_formset'] = p_forms.SupplierFormset(instance=self.object, prefix='supplier')
            context_data['storage_formset'] = p_forms.PartStorageCollectionFormset(instance=self.object, prefix='storage')

        return context_data


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

    fields = (
        'pk',
        'description',
        'part_number',
        'quantity_current',
    )

    headers = {
        'pk': _('ID'),
        'description': _('Description'),
        'part_number': _('Part Number'),
        'quantity_current': _('In Storage'),
    }

    widgets = {
        'pk': TEXT,
        'description': TEXT,
        'part_number': TEXT,
        'quantity_current': False,
    }

    search_fields = {
        'actions': False,
        'quantity_current': False,
    }

    # select_related = (
    #     'unit_service_area__unit',
    #     'unit_service_area__service_area',
    #     'service_type',
    #     'service_status'
    # )

    # def __init__(self, *args, **kwargs):
    #
    #     super(PartsList, self).__init__(*args, **kwargs)
    #     self.templates = {}

    def get_icon(self):
        return 'fa-cog'

    def get_page_title(self, f=None):
        if not f:
            return 'All Parts'

    def format_col(self, field, obj):
        col = super(PartsList, self).format_col(field, obj)
        return col
        # to_return = 'Service Events'
        # filters = f.split('_')
        # for filt in filters:
        #     [key, val] = filt.split('-')
        #     if key == 'ss':
        #         to_return = to_return + ' - Status: ' + models.ServiceEventStatus.objects.get(pk=val).name
        #     elif key == 'ar':
        #         to_return = to_return + ' - Approval is ' + ((not bool(int(val))) * 'not ') + 'required'
        #
        # return to_return

    # def get(self, request, *args, **kwargs):
    #     if self.kwarg_filters is None:
    #         self.kwarg_filters = kwargs.pop('f', None)
    #     return super(PartsList, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(PartsList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        f = self.request.GET.get('f', False)
        context['kwargs'] = {'f': f} if f else {}
        context['page_title'] = self.get_page_title(f)
        return context

    # def get_queryset(self):
    #     qs = super(PartsList, self).get_queryset()
    #
    #     if self.kwarg_filters is None:
    #         self.kwarg_filters = self.request.GET.get('f', None)
    #
    #     # if self.kwarg_filters is not None:
    #     #     filters = self.kwarg_filters.split('_')
    #     #     for filt in filters:
    #     #         [key, val] = filt.split('-')
    #     #         if key == 'ss':
    #     #             qs = qs.filter(service_status=val)
    #     #         elif key == 'ar':
    #     #             qs = qs.filter(is_approval_required=bool(int(val)))
    #     #         elif key == 'ss.ar':
    #     #             qs = qs.filter(service_status__is_approval_required=bool(int(val)))
    #     return qs
