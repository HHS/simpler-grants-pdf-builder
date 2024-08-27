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
