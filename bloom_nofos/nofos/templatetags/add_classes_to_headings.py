from django import template

register = template.Library()


@register.filter()
def add_classes_to_headings(html_string):
    col_span_headers = ["Purpose"]
    if html_string in col_span_headers:
        return "heading--column-span"

    return ""
