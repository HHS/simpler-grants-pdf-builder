from django import template

register = template.Library()


@register.filter()
def subsection_name_or_order(subsection):
    return subsection.name if subsection.name else "(#{})".format(subsection.order)
