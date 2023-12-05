from django import template
from slugify import slugify

register = template.Library()


@register.filter()
def section_id(section):
    if not section.html_id:
        return slugify(section.name)

    return section.html_id
