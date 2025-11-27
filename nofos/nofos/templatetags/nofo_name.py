from django import template

register = template.Library()


@register.filter()
def nofo_name(document):
    return document.short_name or document.title
