import os.path

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.template.defaultfilters import filesizeformat
from django.template.loader import get_template
from django.utils.html import format_html

register = template.Library()


@register.filter
def attachment_link(attachment, label=None, absolute=False):
    href = attachment.attachment.url
    if absolute:
        href = "%s://%s%s" % (settings.HTTP_OR_HTTPS, Site.objects.get_current().domain, href)

    kwargs = {
        'href': href,
        'title': attachment.comment or attachment.attachment.url,
        'label': label or attachment.label or attachment.attachment.name.split("/")[-1],
    }
    return format_html('<a target="_blank" href="{href}" title="{title}">{label}</a>', **kwargs)


@register.filter
def attachment_img(attachment, klass="qa-image"):
    kwargs = {
        'src': attachment.attachment.url,
        'alt': attachment.comment or attachment.label or attachment.attachment.url,
        'klass': klass,
    }
    return format_html('<img class="{klass}" src="{src}" alt="{alt}"/>', **kwargs)


@register.filter
def ti_attachment_img(attachment):
    context = {
        'src': attachment.attachment.url,
        'name': os.path.basename(attachment.attachment.name),
        'size': filesizeformat(attachment.attachment.size),
    }
    return get_template("attachments/ti_img.html").render(context)
