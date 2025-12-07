from composer.utils import (
    get_subsection_status_label,
    get_subsection_status_label_class,
)
from django import template

register = template.Library()


@register.filter
def subsection_status_label(value: str) -> str:
    """
    Translate a subsection.status value into a user-friendly label.
    Usage: {{ subsection.status|subsection_status_label }}
    """
    return get_subsection_status_label(value)


@register.filter
def subsection_status_label_class(value: str) -> str:
    """
    Translate a subsection.status value into a class to apply to the label tag <span>
    Usage: {{ subsection.status|edit_mode_label_class }}
    """
    return get_subsection_status_label_class(value)
