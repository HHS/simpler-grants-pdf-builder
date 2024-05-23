from django import template

register = template.Library()


@register.filter()
def is_floating_callout_box(subsection):
    # this is not the best idea long-term but it works for now
    floating_subsection_strings = [
        "Key facts",
        "Key dates",
        "Questions?",
        "Have questions?",
        "**Have questions?",
    ]

    if subsection.name:
        return subsection.name.strip() in floating_subsection_strings

    for subsection_string in floating_subsection_strings:
        if subsection.body.strip().startswith(subsection_string):
            return True

    return False
