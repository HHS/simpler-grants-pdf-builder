from bs4 import BeautifulSoup, NavigableString
from django import template
from django.utils.safestring import mark_safe

from .utils import (
    _add_class_if_not_exists_to_tag,
    _add_class_if_not_exists_to_tags,
    find_elements_with_character,
    get_parent_td,
)

register = template.Library()

uswds_arrow_upward_icon = '<img class="usa-icon usa-icon--arrow_upward" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/arrow_upward.svg" alt="Report upward trend 123">'
uswds_arrow_downward_icon = '<img class="usa-icon usa-icon--arrow_downward" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/arrow_downward.svg" alt="Report downward trend">'
uswds_check_box_outline_blank_icon = '<img class="usa-icon usa-icon--check_box_outline_blank" src="https://bn-ptzepiewjq-uc.a.run.app/static/img/usa-icons/check_box_outline_blank.svg" alt="Checkbox">'

ICONS = [
    ("↑", uswds_arrow_upward_icon),
    ("↓", uswds_arrow_downward_icon),
    ("◻", uswds_check_box_outline_blank_icon),  # (U+25FB WHITE MEDIUM SQUARE)
    ("☐", uswds_check_box_outline_blank_icon),  # (U+2610 BALLOT BOX)
    ("¨", uswds_check_box_outline_blank_icon),  # (U+00A8 DIAERESIS)
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


def has_checkbox(td):
    if any(x in td.get_text() for x in ["◻", "☐"]):
        return True

    if td.find("img", alt="Checkbox"):
        return True

    return False


def is_list_heading(td):
    if td.find("a"):
        return True

    if td.find("strong") and ":" in td.get_text():
        return True

    return False


def is_before_sublist(td):
    # Find the parent row of the cell
    parent_row = td.find_parent("tr")

    # Iterate over previous siblings (rows above the current one)
    next_row = parent_row.find_next_sibling("tr")
    if next_row:
        first_cell = next_row.find(["td", "th"])
        if first_cell and is_list_heading(first_cell) and not has_checkbox(first_cell):
            return True

    return False


def is_sublist(td):
    # Find the parent row of the cell
    parent_row = td.find_parent("tr")

    # Iterate over previous siblings (rows above the current one)
    prev_row = parent_row.find_previous_sibling("tr")
    if prev_row:
        first_cell = prev_row.find(["td", "th"])
        if first_cell and is_list_heading(first_cell) and not has_checkbox(first_cell):
            return True
        if "usa-icon__td--sublist" in first_cell.get("class", []):
            return True

    return False


def replace_unicode_with_svg(root_element, icon, svg_html):
    found = False
    # Iterate over all elements to find the icon and remove it
    for content in root_element.contents:
        if isinstance(content, NavigableString) and icon in content:
            parts = content.split(icon, 1)  # Split the text at the icon
            new_content = parts[0] + (parts[1] if len(parts) > 1 else "")
            content.replace_with(NavigableString(new_content))
            found = True
            break  # Assuming only one icon per element

    if found:
        # Create the SVG soup
        svg_soup = BeautifulSoup(svg_html, "html.parser")
        # Insert the SVG as the first element in the table cell
        root_element.insert(0, svg_soup)


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

            if td.get_text().count(icon) > 1:
                continue  # Skip this td if it contains multiple instances of the icon

            find_elements_with_character(td, elements_with_char, icon)
            root_elements.extend(elements_with_char)

            for root_element in root_elements:
                # the "bold if required" lis in the logic model tables need this
                _add_class_if_not_exists_to_tags(
                    element=root_element,
                    classname="usa-icon__list-element",
                    tag_names="span|strong|li",
                )

                replace_unicode_with_svg(root_element, icon, svg_html)

                parent_td = get_parent_td(root_element)
                if parent_td:
                    _add_class_if_not_exists_to_tag(
                        element=parent_td, classname="usa-icon__td", tag_name="td"
                    )

                    # add classname for cells which don't have rows with a link above them
                    if is_sublist(parent_td):
                        _add_class_if_not_exists_to_tag(
                            element=parent_td,
                            classname="usa-icon__td--sublist",
                            tag_name="td",
                        )

                    if is_before_sublist(parent_td):
                        # if the next row's first cell has a link and no checkbox
                        _add_class_if_not_exists_to_tag(
                            element=parent_td,
                            classname="usa-icon__td--before-sublist",
                            tag_name="td",
                        )

                    if parent_td.find("a"):
                        _add_class_if_not_exists_to_tag(
                            element=parent_td,
                            classname="usa-icon__td--link",
                            tag_name="td",
                        )

    return mark_safe(str(soup))
