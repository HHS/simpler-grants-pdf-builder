from django import template

from .utils import filter_breadcrumb_sections as _filter_breadcrumb_sections
from .utils import get_breadcrumb_text

register = template.Library()


@register.filter
def filter_breadcrumb_sections(sections):
    return _filter_breadcrumb_sections(sections)


@register.filter
def get_breadcrumb(section_name):
    return get_breadcrumb_text(section_name)
