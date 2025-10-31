from composer.utils import get_edit_mode_label
from django import template

register = template.Library()


@register.filter
def edit_mode_label(value: str) -> str:
    """
    Translate an edit_mode value into a user-friendly label.
    Usage: {{ subsection.edit_mode|edit_mode_label }}
    """
    return get_edit_mode_label(value)
