from django import template
from django.utils.safestring import mark_safe

from .utils import truncate_anchor_links

register = template.Library()


@register.filter()
def truncate_anchor_links_for_docx(html_string):
    return mark_safe(truncate_anchor_links(html_string))
