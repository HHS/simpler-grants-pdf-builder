from django import template

register = template.Library()


@register.filter()
def nofo_section_name_separator(section_name):
    if (
        not section_name
        or not section_name.lower().startswith("step")
        or not ":" in section_name
    ):
        return {"name": section_name, "number": None}

    section_step, section_title, *_ = section_name.split(":")

    section_number = section_step.split(" ")[1]
    return {"name": section_title, "number": section_number}
