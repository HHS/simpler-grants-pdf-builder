from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter()
def get_value_or_none(input, empty_object_name):
    if input:
        return input

    return mark_safe('<i class="text-base">No {}</i>'.format(empty_object_name))
