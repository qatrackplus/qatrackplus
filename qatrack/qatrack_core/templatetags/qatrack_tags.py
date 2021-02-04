import json
import re

from django import template
from django.conf import settings
from django.core.cache import cache
from django.template.loader import get_template
from django.utils import formats, timezone
from django.utils.html import avoid_wrapping
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from qatrack.qatrack_core.dates import format_as_time, format_datetime
from qatrack.service_log import models as sl_models

register = template.Library()


@register.filter(name='addcss')
def addcss(field, css):
    return field.as_widget(attrs={"class": css})


@register.filter(name='addplaceholder')
def addplaceholder(field, placeholder=None):
    if placeholder is None:
        if hasattr(field, 'verbose_name'):
            return field.as_widget(attrs={'placeholder': field.verbose_name})
        v_name = field.name.replace('_', ' ').title()
        return field.as_widget(attrs={'placeholder': v_name})
    else:
        return field.as_widget(attrs={'placeholder': placeholder})


@register.filter(name='addcss_addplaceholder')
def addcss_addplaceholder(field, css):
    if hasattr(field, 'verbose_name'):
        return field.as_widget(attrs={'placeholder': field.verbose_name, 'class': css})
    v_name = re.sub(r'\d', '', field.name.replace('_', ' ').title())
    return field.as_widget(attrs={'placeholder': v_name, 'class': css})


@register.filter(name='hideinput')
def hideinput(field):
    return field.as_widget(attrs={'type': 'hidden'})


@register.filter(name='disableinput')
def disableinput(field):
    return field.as_widget(attrs={'disabled': 'disabled'})


@register.filter
def lookup(d, key):
    return d.get(key)


@register.simple_tag(name='render_status_tag')
def render_status_tag(status_name):
    status = sl_models.ServiceEventStatus.objects.get(name=status_name)
    return '<span class="label smooth-border" style="border-color: %s;">%s</span>' % (
        status.colour, status_name
    )


@register.filter(name='get_user_name')
def get_user_name(user):
    if user is not None:
        return user.username if not user.first_name or not user.last_name else user.first_name + ' ' + user.last_name
    else:
        return ''


@register.simple_tag(name='render_log')
def render_log(service_log, user, link=True, show_rtsqa=False):
    today = timezone.now().date()
    if service_log.datetime.date() == today:
        if timezone.now() - service_log.datetime < timezone.timedelta(hours=1):
            datetime_display = '%s %s' % (
                int((timezone.now() - service_log.datetime).total_seconds() / 60), _('minutes ago')
            )
        else:
            datetime_display = format_as_time(service_log.datetime)
    elif service_log.datetime.date() == today - timezone.timedelta(days=1):
        datetime_display = '%s %s' % (_('Yesterday'), format_as_time(service_log.datetime))
    else:
        datetime_display = format_datetime(service_log.datetime)

    context = {
        'instance': service_log,
        'datetime_display': datetime_display,
        'user': get_user_name(service_log.user),
        'can_view': user.has_perm('service_log.view_serviceevent') and service_log.service_event.is_active and link,
        'show_rtsqa': show_rtsqa
    }
    if service_log.log_type == sl_models.NEW_SERVICE_EVENT:

        return get_template('service_log/log_service_event_new.html').render(context)

    elif service_log.log_type == sl_models.MODIFIED_SERVICE_EVENT:

        try:
            extra_info = json.loads(service_log.extra_info.replace("'", '"'))
        except:  # noqa: E722
            extra_info = service_log.extra_info

        context['extra_info'] = extra_info
        return get_template('service_log/log_service_event_modified.html').render(context)

    elif service_log.log_type == sl_models.STATUS_SERVICE_EVENT:

        try:
            extra_info = json.loads(service_log.extra_info.replace("'", '"'))
        except:  # noqa: E722
            extra_info = service_log.extra_info

        context['extra_info'] = extra_info
        status_old_colour = cache.get(settings.CACHE_SERVICE_STATUS_COLOURS).get(extra_info['status_change']['old'])
        context['old_status_tag'] = '<span class="label smooth-border" style="border-color: %s;">%s</span>' % (
            status_old_colour, extra_info['status_change']['old']
        ) if status_old_colour is not None else extra_info['status_change']['old']

        status_new_colour = cache.get(settings.CACHE_SERVICE_STATUS_COLOURS).get(extra_info['status_change']['new'])
        context['new_status_tag'] = '<span class="label smooth-border" style="border-color: %s;">%s</span>' % (
            status_new_colour, extra_info['status_change']['new']
        ) if status_new_colour is not None else extra_info['status_change']['new']
        context['new_status_colour'] = status_new_colour

        return get_template('service_log/log_service_event_status.html').render(context)

    elif service_log.log_type == sl_models.CHANGED_RTSQA:

        try:
            extra_info = json.loads(service_log.extra_info.replace("'", '"'))
        except:  # noqa: E722
            extra_info = service_log.extra_info

        context['extra_info'] = extra_info
        return get_template('service_log/log_rtsqa.html').render(context)

    elif service_log.log_type == sl_models.DELETED_SERVICE_EVENT:

        try:
            extra_info = json.loads(service_log.extra_info.replace("'", '"'))
        except:  # noqa: E722
            extra_info = service_log.extra_info

        context['extra_info'] = extra_info
        return get_template('service_log/log_service_event_deleted.html').render(context)


@register.filter(is_safe=True)
def filesizeformat(bytes_):
    """
    Format the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB,
    102 bytes, etc.).

    NOTE: Temporarily here to patch an error raised with Python 3.7+ complaining about
    bytes_ being a float instead of an int.
    """
    try:
        bytes_ = int(float(bytes_))
    except (TypeError, ValueError, UnicodeDecodeError):
        value = ngettext("%(size)d byte", "%(size)d bytes", 0) % {'size': 0}
        return avoid_wrapping(value)

    def filesize_number_format(value):
        return formats.number_format(round(value, 1), 1)

    KB = 1 << 10
    MB = 1 << 20
    GB = 1 << 30
    TB = 1 << 40
    PB = 1 << 50

    negative = bytes_ < 0
    if negative:
        bytes_ = -bytes_  # Allow formatting of negative numbers.

    if bytes_ < KB:
        value = ngettext("%(size)d byte", "%(size)d bytes", bytes_) % {'size': bytes_}
    elif bytes_ < MB:
        value = _("%s KB") % filesize_number_format(bytes_ / KB)
    elif bytes_ < GB:
        value = _("%s MB") % filesize_number_format(bytes_ / MB)
    elif bytes_ < TB:
        value = _("%s GB") % filesize_number_format(bytes_ / GB)
    elif bytes_ < PB:
        value = _("%s TB") % filesize_number_format(bytes_ / TB)
    else:
        value = _("%s PB") % filesize_number_format(bytes_ / PB)

    if negative:
        value = "-%s" % value
    return avoid_wrapping(value)
