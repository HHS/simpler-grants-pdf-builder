from django import template
from django.utils.safestring import mark_safe


from bs4 import BeautifulSoup

from .utils import find_elements_with_character, get_parent_td

register = template.Library()

uswds_arrow_upward_icon = '<img class="usa-icon usa-icon--list usa-icon--arrow_upward" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/arrow_upward.svg" alt="Report upward trend 123">'
uswds_arrow_downward_icon = '<img class="usa-icon usa-icon--list usa-icon--arrow_downward" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/arrow_downward.svg" alt="Report downward trend">'
uswds_check_box_outline_blank_icon = '<img class="usa-icon usa-icon--check_box_outline_blank" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/check_box_outline_blank.svg" alt="Checkbox">'


ICONS = [
    ("↑", uswds_arrow_upward_icon),
    ("↓", uswds_arrow_downward_icon),
    ("◻", uswds_check_box_outline_blank_icon),
]


# TODO add some tests
def has_link_in_above_rows(td):
    # Find the parent row of the cell
    parent_row = td.find_parent("tr")

    # Iterate over previous siblings (rows above the current one)
    for sibling in parent_row.find_previous_siblings("tr"):
        first_cell = sibling.find(["td", "th"])
        if first_cell and first_cell.find("a"):
            return True

    return False


def has_link_in_next_row(td):
    # Find the parent row of the cell
    parent_row = td.find_parent("tr")

    # Iterate over previous siblings (rows above the current one)
    next_row = parent_row.find_next_sibling("tr")
    if next_row:
        first_cell = next_row.find(["td", "th"])
        if first_cell and first_cell.find("a"):
            return True

    return False


def add_class_if_not_exists_to_tag(element, classname, tag_name=None):
    if classname not in element.get("class", []):
        if tag_name and element.name == tag_name:
            element["class"] = element.get("class", []) + [classname]


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
                add_class_if_not_exists_to_tag(
                    element=root_element,
                    classname="usa-icon__list-element",
                    tag_name="span",
                )
                root_element.string = root_element.text.replace(icon, "")
                root_element.insert(0, BeautifulSoup(svg_html, "html.parser"))

                parent_td = get_parent_td(root_element)
                if parent_td:
                    add_class_if_not_exists_to_tag(
                        element=parent_td, classname="usa-icon__td", tag_name="td"
                    )

                    # add classname for cells which don't have rows with a link above them
                    if has_link_in_above_rows(parent_td):
                        add_class_if_not_exists_to_tag(
                            element=parent_td,
                            classname="usa-icon__td--sublist",
                            tag_name="td",
                        )

                    if has_link_in_next_row(parent_td):
                        add_class_if_not_exists_to_tag(
                            element=parent_td,
                            classname="usa-icon__td--before-sublist",
                            tag_name="td",
                        )

    return mark_safe(str(soup))
