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

    # The part before the colon is not guaranteed to be "Step <n>". A name like
    # "Steps: Review the Opportunity" passes the checks above but has no space,
    # so there is no number to take.
    step_parts = section_step.split(" ")
    section_number = step_parts[1] if len(step_parts) > 1 else None
    return {"name": section_title, "number": section_number}
