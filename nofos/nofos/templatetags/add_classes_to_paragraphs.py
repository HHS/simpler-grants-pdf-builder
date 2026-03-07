import re

from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

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
