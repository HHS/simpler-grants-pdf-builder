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
    for p in soup.find_all("p", string=re.compile("\(Maximum points:", re.IGNORECASE)):
        _add_class_if_not_exists_to_tag(p, "heading--max-points", "p")
        p["role"] = "heading"
        p["aria-level"] = "7"

    # Look for paragraphs that contain the string "page-break-before"
    for p in soup.find_all("p", string="page-break-before"):
        _add_class_if_not_exists_to_tag(p, "page-break-before page-break--spacer", "p")

    for p in soup.find_all("p", string="page-break-after"):
        _add_class_if_not_exists_to_tag(p, "page-break-after page-break--spacer", "p")

    return mark_safe(str(soup))
