from bs4 import BeautifulSoup
from django import template

register = template.Library()


@register.filter
def add_classes_to_toc(nofo):
    """
    Custom filter to calculate the number of ToC items for a given NOFO object.

    Args:
        nofo (object): The NOFO object containing sections and HTML content.

    Returns:
        int: Total count of ToC items.
    """
    count = 0

    # Count sections
    sections = nofo.sections.all().order_by("order")
    count += len(sections)

    for section in sections:
        if section.has_section_page and "contacts" not in section.name.lower():
            for subsection in section.subsections.all().order_by("order"):
                if subsection.tag == "h3":
                    count += 1

    # before you begin page is not a section so not counted above
    count += 1

    toc_class = "toc--normal" if count <= 23 else "toc--small"

    return "{} toc--items--{}".format(toc_class, count)
