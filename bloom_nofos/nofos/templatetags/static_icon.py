from django import template
from django.templatetags.static import static

register = template.Library()

from .utils import get_icon_from_theme


@register.simple_tag
def static_icon(icon_name="", theme="", section=""):
    return static(get_icon_from_theme(icon_name, theme, section))
