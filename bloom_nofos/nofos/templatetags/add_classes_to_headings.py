from django import template

register = template.Library()


@register.filter()
def add_classes_to_headings(content):
    col_span_headers = ["Purpose"]
    if content in col_span_headers:
        return "heading--column-span"

    return ""
