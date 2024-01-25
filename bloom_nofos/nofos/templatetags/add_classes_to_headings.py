from django import template

register = template.Library()


@register.filter()
def add_classes_to_headings(content):
    page_break_headers = ["Application checklist", "Reporting"]
    if content in page_break_headers:
        return "page-break-before--heading"

    col_span_headers = ["Purpose"]
    if content in col_span_headers:
        return "heading--column-span"

    return ""
