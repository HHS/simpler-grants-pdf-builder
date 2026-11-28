import re

from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from ..note_paragraphs import (
    is_between_list_items,
    is_in_list_or_table,
    is_note_paragraph,
)
from .utils import _add_class_if_not_exists_to_tag

register = template.Library()


@register.filter()
def add_classes_to_paragraphs(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    # Look paragraphs that contain a string like "(Maximum points:"
    for p in soup.find_all("p", string=re.compile(r"\(Maximum points:", re.IGNORECASE)):
        _add_class_if_not_exists_to_tag(p, "heading--max-points", "p")
        p["role"] = "heading"
        p["aria-level"] = "7"

    return mark_safe(str(soup))


@register.filter
def keep_tables_with_following_notes(html_string):
    """Keep a table on the same page as a standalone "Note:" paragraph after it.

    Notes get no paragraph styling of their own: imported standalone notes are
    note callout subsections (#1437). Notes in list items, table cells or
    between two items of one list are ordinary paragraphs.
    """
    soup = BeautifulSoup(html_string, "html.parser")
    for element in soup.find_all("p"):
        if is_in_list_or_table(element) or not is_note_paragraph(element):
            continue
        if is_between_list_items(element):
            continue
        for previous in element.previous_siblings:
            if not getattr(previous, "name", None):
                if str(previous).strip():
                    break
                continue
            if (
                previous.name == "p"
                and not previous.get_text(strip=True)
                and not previous.find(True)
            ):
                continue
            if previous.name == "table":
                _add_class_if_not_exists_to_tag(
                    previous, "table--with-following-note", "table"
                )
            break
    return mark_safe(str(soup))


@register.filter
def add_class_to_first_paragraph(html_string, class_name="instructions-heading"):
    soup = BeautifulSoup(html_string, "html.parser")
    first_p = soup.find("p")

    if not first_p:
        return str(soup)

    existing_classes = first_p.get("class", [])
    if class_name not in existing_classes:
        existing_classes.append(class_name)
        first_p["class"] = existing_classes

    return str(soup)
