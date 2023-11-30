from django import template

register = template.Library()


@register.filter()
def nofo_name(nofo):
    return nofo.short_name or nofo.title
