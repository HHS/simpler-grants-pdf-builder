from composer.utils import get_edit_mode_label_class
from django import template

register = template.Library()


@register.filter
def edit_mode_label_class(value: str) -> str:
    """
    Translate an edit_mode value into a class to apply to the label tag <span>
    Usage: {{ subsection.edit_mode|edit_mode_label_class }}
    """
    return get_edit_mode_label_class(value)
