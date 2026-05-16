from django import template
from django.contrib.staticfiles.storage import staticfiles_storage

register = template.Library()


@register.simple_tag
def static_url(path):
    """Return the full URL to a static file"""
    return staticfiles_storage.url(path)
