from bs4 import BeautifulSoup, NavigableString, Tag
from django import template
from django.utils.safestring import mark_safe

from .utils import (
    _add_class_if_not_exists_to_tag,
    _add_class_if_not_exists_to_tags,
    find_elements_with_character,
    get_parent_td,
    match_numbered_sublist,
)

register = template.Library()

uswds_arrow_upward_icon = '<img class="usa-icon usa-icon--arrow_upward" src="/static/img/usa-icons/arrow_upward.svg" alt="Report upward trend">'
uswds_arrow_downward_icon = '<img class="usa-icon usa-icon--arrow_downward" src="/static/img/usa-icons/arrow_downward.svg" alt="Report downward trend">'
uswds_check_box_outline_blank_icon = '<img class="usa-icon usa-icon--check_box_outline_blank" src="/static/img/usa-icons/check_box_outline_blank.svg" alt="Checkbox">'

ICONS = [
    ("↑", uswds_arrow_upward_icon),
    ("↓", uswds_arrow_downward_icon),
    ("◻", uswds_check_box_outline_blank_icon),  # (◻) U+25FB WHITE MEDIUM SQUARE
]


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
    if td.find("a") and not has_checkbox(td):
        return True

    if td.find("strong") and ":" in td.get_text():
        return True

    if (
        td.text.lower().startswith("other required forms")
        or td.text.lower() == "attachments"
        or td.text.lower() == "narratives"
    ):
        return True

    return False


def is_before_sublist(td):
    # Find the parent row of the cell
    parent_row = td.find_parent("tr")

    # Iterate over previous siblings (rows above the current one)
    next_row = parent_row.find_next_sibling("tr")
    if next_row:
        first_cell = next_row.find(["td", "th"])
        if first_cell:
            if is_list_heading(first_cell) and not has_checkbox(first_cell):
                return True
            # if current cell is a numbered sublist next cell isn't
            if is_numbered_sublist(td) and not is_numbered_sublist(first_cell):
                return True

    return False


def is_numbered_sublist(td):
    td_text = td.text.replace("◻", "").strip()
    return match_numbered_sublist(td_text)


def is_sublist(td):
    # Find the parent row of the cell
    parent_row = td.find_parent("tr")

    # Iterate over previous siblings (rows above the current one)
    prev_row = parent_row.find_previous_sibling("tr")
    if prev_row:
        first_cell = prev_row.find(["td", "th"])
        if first_cell and is_list_heading(first_cell) and not has_checkbox(first_cell):
            return True
        if "usa-icon__td--sublist" in first_cell.get(
            "class", []
        ) and "usa-icon__td--sublist--numbered" not in first_cell.get("class", []):
            return True

    return False


def replace_unicode_with_svg(root_element, icon, svg_html):
    icon_count = root_element.get_text().count(icon)

    if icon_count > 1:
        # Look for child elements with exactly one icon
        for child in root_element.find_all(recursive=True):
            if isinstance(child, Tag) and child.get_text().count(icon) == 1:
                # Recursively call replace_unicode_with_svg on elements with just 1 icon
                replace_unicode_with_svg(child, icon, svg_html)
        return

    found = False
    # Iterate over all elements to find the icon and remove it
    for content in root_element.contents:
        if isinstance(content, NavigableString) and icon in content:
            parts = content.split(icon, 1)  # Split the text at the icon
            new_content = parts[0] + (parts[1] if len(parts) > 1 else "")
            content.replace_with(NavigableString(new_content))
            found = True
            break

    if found:
        # Create the SVG soup
        svg_soup = BeautifulSoup(svg_html, "html.parser")
        # Insert the SVG as the first element in the table cell
        root_element.insert(0, svg_soup)


def wrap_text_in_span(td):
    soup = BeautifulSoup("", "html.parser")

    img = td.find("img")
    if img and img.next_sibling and isinstance(img.next_sibling, NavigableString):
        # Get the text after the image
        text = img.next_sibling.strip()

        if text:
            # Create a new span element with the text
            text_wrapped_with_span = soup.new_tag("span")
            text_wrapped_with_span.string = text
            img.next_sibling.replace_with(text_wrapped_with_span)


def wrap_td_contents_in_div(td):
    first_child = td.contents[0] if td.contents else None
    if first_child and first_child.name == "div":
        return  # If the first child is a div, do nothing

    soup = BeautifulSoup("", "html.parser")

    # Create a new div element
    new_div = soup.new_tag("div")

    # Move all the contents of td into the new div by iterating over a copy of td.contents
    for content in list(td.contents):
        new_div.append(content)

    # Clear the original contents of td and add the new div
    td.clear()
    td.append(new_div)


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
                    if is_list_heading(parent_td):
                        _add_class_if_not_exists_to_tag(
                            element=parent_td,
                            classname="usa-icon__td--list-heading",
                            tag_name="td",
                        )

                    # add classname for cells which don't have rows with a link above them
                    if is_sublist(parent_td):
                        _add_class_if_not_exists_to_tag(
                            element=parent_td,
                            classname="usa-icon__td--sublist",
                            tag_name="td",
                        )

                    # add classnames for sublist cells which are numbered "1. Work plan"
                    if is_numbered_sublist(parent_td):
                        _add_class_if_not_exists_to_tag(
                            element=parent_td,
                            classname="usa-icon__td--sublist",
                            tag_name="td",
                        )
                        _add_class_if_not_exists_to_tag(
                            element=parent_td,
                            classname="usa-icon__td--sublist--numbered",
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

                    wrap_text_in_span(parent_td)
                    wrap_td_contents_in_div(parent_td)

    return mark_safe(str(soup))
