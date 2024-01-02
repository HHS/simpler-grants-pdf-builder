from django import template

register = template.Library()

from ..nofo import get_icon_for_section


@register.filter()
def get_icon_for_section(section_name="", theme="blue"):
    return get_icon_for_section(section_name, theme)
