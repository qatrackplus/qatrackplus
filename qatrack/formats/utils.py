from django.conf import settings
from django.utils.formats import get_format


def get_js_format(name):
    """Resolve locale-specific JS format with fallback to English/default settings."""
    resolved = get_format(name)
    if resolved == name:
        resolved = get_format(name, lang='en')
    if resolved == name:
        resolved = getattr(settings, name, name)
    return resolved
