from django import template

register = template.Library()


@register.filter()
def add_classes_to_headings(content):
    heading_text = ["Application checklist", "Reporting"]
    if content in heading_text:
        return "heading--break-page"
    return ""
