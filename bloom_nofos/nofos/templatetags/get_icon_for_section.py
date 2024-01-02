from django import template

register = template.Library()

from .utils import get_icon_for_section as get_icon_for_section_func


@register.filter()
def get_icon_for_section(section_name=""):
    return get_icon_for_section_func(section_name)
