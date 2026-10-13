from django import template

from .utils import (
    is_application_due_date_callout as is_application_due_date_callout_func,
)
from .utils import is_floating_callout_box as is_floating_callout_box_func

register = template.Library()


@register.filter()
def is_floating_callout_box(subsection):
    return is_floating_callout_box_func(subsection)


@register.filter()
def is_application_due_date_callout(subsection):
    return is_application_due_date_callout_func(subsection)
