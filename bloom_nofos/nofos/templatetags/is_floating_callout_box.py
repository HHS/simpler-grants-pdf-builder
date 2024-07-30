from django import template

from .utils import is_floating_callout_box as is_floating_callout_box_func

register = template.Library()


@register.filter()
def is_floating_callout_box(subsection):
    return is_floating_callout_box_func(subsection)
