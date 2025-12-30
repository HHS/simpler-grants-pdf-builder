from typing import Dict

from composer.utils import do_replace_variable_keys_with_values
from django import template

register = template.Library()


@register.filter
def replace_variable_keys_with_values(html_string, variables_dict):
    return do_replace_variable_keys_with_values(html_string, variables_dict)
