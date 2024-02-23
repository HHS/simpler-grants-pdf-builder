from django import template
from django.templatetags.static import static

register = template.Library()

from .utils import get_icon_from_theme


@register.simple_tag
def static_icon(icon_name="", theme="", section="", nofo=None):
    nofo_number = ""
    nofo_icon_path = ""
    if nofo:
        nofo_number = nofo.number
        nofo_icon_path = nofo.icon_path
    return static(
        get_icon_from_theme(icon_name, theme, section, nofo_number, nofo_icon_path)
    )
