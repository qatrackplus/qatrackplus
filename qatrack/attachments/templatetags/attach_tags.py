import os.path

from django import template
from django.utils.html import format_html
from django.template.defaultfilters import filesizeformat
from django.template.loader import get_template

register = template.Library()


@register.filter
def attachment_link(attachment):
    kwargs = {
        'href': attachment.attachment.url,
        'title': attachment.comment or attachment.attachment.url,
        'label': attachment.label or attachment.attachment.name.split("/")[-1],
    }
    return format_html('<a target="_blank" href="{href}" title="{title}">{label}</a>', **kwargs)


@register.filter
def attachment_img(attachment):
    kwargs = {
        'src': attachment.attachment.url,
        'alt': attachment.comment or attachment.label or attachment.attachment.url,
    }
    return format_html('<img class="qa-image" src="{src}" alt="{alt}"/>', **kwargs)


@register.filter
def ti_attachment_img(attachment):
    context = {
        'src': attachment.attachment.url,
        'name': os.path.basename(attachment.attachment.name),
        'size': filesizeformat(attachment.attachment.size),
    }
    return get_template("attachments/ti_img.html").render(context)
