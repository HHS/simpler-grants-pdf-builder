from django import template
from django.utils.safestring import mark_safe


from bs4 import BeautifulSoup

from .utils import find_elements_with_character, get_parent_td

register = template.Library()

uswds_arrow_upward_icon = '<img class="usa-icon usa-icon--list usa-icon--arrow_upward" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/arrow_upward.svg" alt="Report upward trend" />'
uswds_arrow_downward_icon = '<img class="usa-icon usa-icon--list usa-icon--arrow_downward" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/arrow_downward.svg" alt="Report downward trend" />'
uswds_check_box_outline_blank_icon = '<img class="usa-icon usa-icon--check_box_outline_blank" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/check_box_outline_blank.svg" alt="Checkbox" />'


ICONS = [
    ("↑", uswds_arrow_upward_icon),
    ("↓", uswds_arrow_downward_icon),
    ("◻", uswds_check_box_outline_blank_icon),
]


@register.filter()
def replace_unicode_with_icon(html_string):
    """
    Replaces unicode characters with SVG icon images in table cells.

    Parses the HTML string into a BeautifulSoup object.
    Finds all <td> elements.
    For each icon character and SVG icon pair:
      - Finds all elements containing the icon character within each <td>.
      - Adds CSS classes to those elements and their parent <td>.
      - Replaces the icon character with the SVG icon HTML.
    """
    soup = BeautifulSoup(html_string, "html.parser")
    tds = soup.find_all("td")

    for icon, svg_html in ICONS:
        root_elements = []

        for td in tds:
            elements_with_char = []
            find_elements_with_character(td, elements_with_char, icon)
            root_elements.extend(elements_with_char)

            for root_element in root_elements:
                root_element["class"] = root_element.get("class", []) + [
                    "usa-icon--list__element"
                ]
                root_element.string = root_element.text.replace(icon, "")
                root_element.insert(0, BeautifulSoup(svg_html, "html.parser"))

                parent_td = get_parent_td(root_element)
                if parent_td:
                    td_classname = "usa-icon--list__td"
                    if td_classname not in parent_td.get("class", []):
                        parent_td["class"] = parent_td.get("class", []) + [td_classname]

    return mark_safe(str(soup))
