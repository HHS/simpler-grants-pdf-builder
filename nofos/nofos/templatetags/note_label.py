from django import template
from django.utils.safestring import mark_safe

from ..note_paragraphs import has_note_label as has_note_label_func
from ..note_paragraphs import mark_note_lead_in as mark_note_lead_in_func

register = template.Library()


@register.filter
def has_note_label(markdown):
    return has_note_label_func(markdown)


@register.filter
def mark_note_lead_in(html):
    return mark_safe(mark_note_lead_in_func(html))
