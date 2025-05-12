from django import template

register = template.Library()


@register.filter()
def input_type(input):
    return input.field.widget.__class__.__name__
