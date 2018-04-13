
import json

from braces.views import PermissionRequiredMixin
from django.conf import settings
from django.core.urlresolvers import reverse, resolve
from django.utils import timezone
from django.db.models import ObjectDoesNotExist, F
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
        'date_acceptance': u.date_acceptance.strftime('%Y-%m-%d') if u.date_acceptance else None,
        'available_time_edits': {
            uate.date.strftime('%Y-%m-%d'): {
                'name': uate.name,
                'hours': uate.hours
            } for uate in u.unitavailabletimeedit_set.all()
        },
        'available_times': list(u.unitavailabletime_set.all().values())
    } for u in unit_qs}

    return JsonResponse({'unit_available_time_data': unit_available_time_data})


class UnitAvailableTimeChange(PermissionRequiredMixin, TemplateView):

    permission_required = 'units.change_unitavailabletime'
    raise_exception = True
    template_name = 'units/unit_available_time_change.html'

    def get_context_data(self, **kwargs):
        context = super(UnitAvailableTimeChange, self).get_context_data(**kwargs)
        context['unit_availble_time_form'] = forms.UnitAvailableTimeForm()
        context['unit_availble_time_edit_form'] = forms.UnitAvailableTimeEditForm()
        context['units'] = u_models.Unit.objects.all()
        return context


def handle_unit_available_time(request):

    delete = request.POST.get('delete') == 'true'
    units = request.POST.getlist('units[]')
    days = [timezone.datetime.fromtimestamp(int(d) / 1000, timezone.utc).date() for d in request.POST.getlist('days[]', [])]

    uats = u_models.UnitAvailableTime.objects.filter(unit__in=units, date_changed__in=days).select_related('unit')

    if delete:
        uats.exclude(date_changed=F('unit__date_acceptance')).delete()
        return get_unit_available_time_data(request)

    hours = {'monday': ['0', '0'], 'tuesday': ['0', '0'], 'wednesday': ['0', '0'], 'thursday': ['0', '0'],
             'friday': ['0', '0'], 'saturday': ['0', '0'], 'sunday': ['0', '0']}

    for h in hours:
        hours_min = request.POST.get('hours_' + h).replace('_', '0')
        if hours_min != '':
            hours_min = hours_min.split(':')
            hours[h] = hours_min

    for uat in uats:
        for h in hours:
            setattr(uat, 'hours_' + h, timezone.timedelta(hours=int(hours[h][0]), minutes=int(hours[h][1])))
        uat.save()

    for unit in u_models.Unit.objects.filter(id__in=units):
        if days[0] > unit.date_acceptance and len(uats.filter(unit=unit, date_changed=days[0])) == 0:
            u_models.UnitAvailableTime.objects.create(
                unit=unit,
                date_changed=days[0],
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

    delete = request.POST.get('delete', False) == 'true'
    units = [u_models.Unit.objects.get(id=u_id) for u_id in request.POST.getlist('units[]', [])]
    days = [timezone.datetime.fromtimestamp(int(d) / 1000, timezone.utc).date() for d in request.POST.getlist('days[]', [])]

    if delete:
        uates = u_models.UnitAvailableTimeEdit.objects.filter(unit__in=units, date__in=days)
        uates.delete()
        return get_unit_available_time_data(request)

    hours_mins = request.POST.get('hours_mins', None)
    if hours_mins:
        hours_mins = hours_mins.replace('_', '0').split(':')
        hours = int(hours_mins[0])
        mins = int(hours_mins[1])
        name = request.POST.get('name', None)

        for d in days:
            for u in units:
                if d < u.date_acceptance:
                    continue
                try:
                    uate = u_models.UnitAvailableTimeEdit.objects.get(unit=u, date=d)
                    uate.hours = timezone.timedelta(hours=hours, minutes=mins)
                    uate.name = name
                    uate.save()
                except ObjectDoesNotExist:
                    u_models.UnitAvailableTimeEdit.objects.create(
                        unit=u, date=d, hours=timezone.timedelta(hours=hours, minutes=mins), name=name
                    )

    return get_unit_available_time_data(request)
