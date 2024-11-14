from django import template

register = template.Library()


@register.filter()
def add_classes_to_headings(html_string):
    col_span_headers = ["Purpose"]
    if html_string in col_span_headers:
        return "heading--column-span"

    return ""


@register.filter()
def add_classes_to_nofo_title(nofo_title):
    if len(nofo_title) > 170:
        return "nofo--cover-page--title--h1--very-smol"

    if len(nofo_title) > 120:
        return "nofo--cover-page--title--h1--smaller"

    return "nofo--cover-page--title--h1--normal"
