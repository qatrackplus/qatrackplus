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


# class SmartSpacelessNode(template.Node):
#     def __init__(self, nodelist):
#         self.nodelist = nodelist
#
#     def render(self, context):
#         content = self.nodelist.render(context)
#         print content
#         print content.strip()
#         print strip_spaces_between_tags(content.strip())
#         return strip_spaces_between_tags(content.strip())
#
#
# @register.tag
# def smart_spaceless(parser, token):
#     """
#     Removes whitespace between HTML tags, including tab and newline characters,
#     but only if settings.DEBUG = False
#
#     Example usage:
#         {% load template_additions %}
#         {% smart_spaceless %}
#             <p>
#                 <a href="foo/">Foo</a>
#             </p>
#         {% end_smart_spaceless %}
#
#     This example would return this HTML:
#
#         <p><a href="foo/">Foo</a></p>
#
#     Only space between *tags* is normalized -- not space between tags and text.
#     In this example, the space around ``Hello`` won't be stripped:
#
#         {% smart_spaceless %}
#             <strong>
#                 Hello
#             </strong>
#         {% end_smart_spaceless %}
#     """
#     nodelist = parser.parse(('end_smart_spaceless',))
#     parser.delete_first_token()
#     return SmartSpacelessNode(nodelist)
