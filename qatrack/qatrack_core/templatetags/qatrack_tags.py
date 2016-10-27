import re

from django import template
from django.utils.html import strip_tags

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
    return d[key]
