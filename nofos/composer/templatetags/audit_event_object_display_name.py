from composer.utils import get_audit_event_object_display_name
from django import template

register = template.Library()


@register.filter
def audit_event_object_display_name(value: str) -> str:
    """
    Translate an object_name value into a user-friendly display version.
    Usage: {{ event.object_type|audit_event_object_display_name }}
    """
    return get_audit_event_object_display_name(value)
