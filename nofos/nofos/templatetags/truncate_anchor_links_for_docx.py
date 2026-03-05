from django import template
from django.utils.safestring import mark_safe

from .utils import truncate_anchor_links, truncate_heading_ids

register = template.Library()


@register.filter()
def truncate_anchor_links_for_docx(html_string):
    return mark_safe(truncate_anchor_links(html_string))


@register.filter()
def truncate_heading_ids_for_docx(value):
    return truncate_heading_ids(value)
