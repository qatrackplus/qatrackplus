from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def part_list_in_storage(s):

    psc = s.partstoragecollection_set.all()

    if len(psc) == 0:
        return ''

    if len(psc) == 1:
        div = '<div class="part-list-container one"><div class="part-list">%s</div></div>'
    else:
        div = '<div class="part-list-container"><div class="box-shadow"></div><div class="part-list">%s</div></div>'

    parts_html = '<ul>'
    for p in psc:
        href = reverse(
            'part_details',
            # 'admin:%s_%s_change' % ('parts',  'part'),
            args=[p.part.id]
        )
        parts_html += '<li class="part_list_entry"><a href="%s">(%s) - %s</a></li>' % (
            href, p.quantity, p.part
        )
    parts_html += '</ul>'

    return mark_safe(div % parts_html)
