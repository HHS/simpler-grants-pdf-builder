from django import template

register = template.Library()

from .utils import add_class_to_nofo_title


@register.filter()
def add_classes_to_headings(html_string):
    col_span_headers = ["Purpose"]
    if html_string in col_span_headers:
        return "heading--column-span"

    return ""


@register.filter()
def add_classes_to_nofo_title(nofo_title):
    return add_class_to_nofo_title(nofo_title)
