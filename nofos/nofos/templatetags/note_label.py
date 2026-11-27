from django import template

from ..note_paragraphs import has_note_label as has_note_label_func

register = template.Library()


@register.filter
def has_note_label(markdown):
    return has_note_label_func(markdown)
