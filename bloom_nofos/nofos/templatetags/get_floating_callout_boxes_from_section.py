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


@register.filter()
def get_combined_wordcount_for_subsections(subsections):
    word_count = 0
    for subsection in subsections:
        word_count += len(subsection.body.split())

    return word_count
