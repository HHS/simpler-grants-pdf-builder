from django import template

from .utils import is_floating_callout_box

register = template.Library()


@register.filter()
def get_floating_callout_boxes_from_section(section):
    return [
        subsection
        for subsection in section.subsections.all().order_by("order")
        if subsection.callout_box and is_floating_callout_box(subsection)
    ]
