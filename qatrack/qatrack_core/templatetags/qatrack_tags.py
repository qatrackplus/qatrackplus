import re

from django import template
register = template.Library()


@register.filter(name='addcss')
def addcss(field, css):
    return field.as_widget(attrs={"class": css})


@register.filter(name='addplaceholder')
def addplaceholder(field):
    if hasattr(field, 'verbose_name'):
        return field.as_widget(attrs={'placeholder': field.verbose_name})
    v_name = field.name.replace('_', ' ').title()
    return field.as_widget(attrs={'placeholder': v_name})


@register.filter(name='custominput')
def custominput(field, css):
    if hasattr(field, 'verbose_name'):
        return field.as_widget(attrs={'placeholder': field.verbose_name, 'class': css})
    v_name = re.sub(r'\d', '', field.name.replace('_', ' ').title())
    return field.as_widget(attrs={'placeholder': v_name, 'class': css})


@register.filter(name='hideinput')
def hideinput(field):
    return field.as_widget(attrs={'type': 'hidden'})
