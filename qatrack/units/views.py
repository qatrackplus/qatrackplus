from braces.views import PermissionRequiredMixin
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import Permission
from django.db.models import ObjectDoesNotExist
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView
import pytz

from qatrack.qatrack_core.dates import format_as_date as fmt_date
from qatrack.qatrack_core.serializers import QATrackJSONEncoder
from qatrack.units import forms
from qatrack.units import models as u_models


def get_unit_available_time_data(request):

    unit_qs = u_models.Unit.objects.prefetch_related('unitavailabletime_set', 'unitavailabletimeedit_set').all()
    unit_available_time_data = {
        u.id: {
            'number': u.number,
            'name': u.name,
            'active': u.active,
            'date_acceptance': fmt_date(u.date_acceptance) if u.date_acceptance else None,
            'available_time_edits': {
                fmt_date(uate.date): {
                    'name': uate.name,
                    'hours': uate.hours
                } for uate in u.unitavailabletimeedit_set.all()
            },
            'available_times': u.get_available_times_list(),
        } for u in unit_qs
    }

    return JsonResponse({'unit_available_time_data': unit_available_time_data})


class UnitAvailableTimeChange(PermissionRequiredMixin, TemplateView):

    permission_required = 'units.change_unitavailabletime'
    raise_exception = True
    template_name = 'units/unit_available_time_change.html'

    def get_context_data(self, **kwargs):
        context = super(UnitAvailableTimeChange, self).get_context_data(**kwargs)
        context['unit_available_time_form'] = forms.UnitAvailableTimeForm()
        context['unit_available_time_edit_form'] = forms.UnitAvailableTimeEditForm()
        context['units'] = u_models.Unit.objects.filter(is_serviceable=True)
        context['year_select'] = forms.year_select
        context['month_select'] = forms.month_select
        return context


@permission_required(Permission.objects.filter(codename='change_unitavailabletime'))
@csrf_protect
def handle_unit_available_time(request):

    units = request.POST.getlist('units[]')
    tz = request.POST.get("tz", settings.TIME_ZONE)
    tz = pytz.timezone(tz)
    day = request.POST.get('day')
    day = timezone.localtime(timezone.datetime.fromtimestamp(int(day) / 1000, tz)).date() if day else None

    uats = u_models.UnitAvailableTime.objects.filter(unit__in=units, date_changed=day).select_related('unit')

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
        if day > unit.date_acceptance and len(uats.filter(unit=unit, date_changed=day)) == 0:
            u_models.UnitAvailableTime.objects.create(
                unit=unit,
                date_changed=day,
                hours_monday=timezone.timedelta(hours=int(hours['monday'][0]), minutes=int(hours['monday'][1])),
                hours_tuesday=timezone.timedelta(hours=int(hours['tuesday'][0]), minutes=int(hours['tuesday'][1])),
                hours_wednesday=timezone.timedelta(hours=int(hours['wednesday'][0]), minutes=int(hours['wednesday'][1])),  # noqa: E501
                hours_thursday=timezone.timedelta(hours=int(hours['thursday'][0]), minutes=int(hours['thursday'][1])),
                hours_friday=timezone.timedelta(hours=int(hours['friday'][0]), minutes=int(hours['friday'][1])),
                hours_saturday=timezone.timedelta(hours=int(hours['saturday'][0]), minutes=int(hours['saturday'][1])),
                hours_sunday=timezone.timedelta(hours=int(hours['sunday'][0]), minutes=int(hours['sunday'][1])),
            )

    return get_unit_available_time_data(request)


@permission_required(Permission.objects.filter(codename='change_unitavailabletime'))
@csrf_protect
def handle_unit_available_time_edit(request):

    units = [u_models.Unit.objects.get(id=u_id) for u_id in request.POST.getlist('units[]', [])]
    tz = request.POST.get("tz", settings.TIME_ZONE)
    tz = pytz.timezone(tz)
    days = [timezone.localtime(timezone.datetime.fromtimestamp(int(d) / 1000, tz)).date() for d in request.POST.getlist('days[]', [])]  # noqa: E501

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
                        unit=u,
                        date=d,
                        hours=timezone.timedelta(hours=hours, minutes=mins),
                        name=name,
                    )

    return get_unit_available_time_data(request)


@permission_required(Permission.objects.filter(codename='change_unitavailabletime'))
@csrf_protect
def delete_schedules(request):

    unit_ids = request.POST.getlist('units[]', [])
    tz = request.POST.get("tz", settings.TIME_ZONE)
    tz = pytz.timezone(tz)
    days = [
        timezone.localtime(timezone.datetime.fromtimestamp(int(d) / 1000, tz)).date()
        for d in request.POST.getlist('days[]', [])
    ]

    u_models.UnitAvailableTime.objects.filter(
        unit_id__in=unit_ids,
        date_changed__in=days
    ).delete()

    u_models.UnitAvailableTimeEdit.objects.filter(
        unit_id__in=unit_ids,
        date__in=days
    ).delete()

    return get_unit_available_time_data(request)


def get_unit_info(request):
    units = request.GET.getlist("units[]", [])
    serviceable_only = request.GET.get("serviceable_only", "false") == "true"
    unit_info = u_models.get_unit_info(unit_ids=units, serviceable_only=serviceable_only)
    return JsonResponse(unit_info, encoder=QATrackJSONEncoder)
