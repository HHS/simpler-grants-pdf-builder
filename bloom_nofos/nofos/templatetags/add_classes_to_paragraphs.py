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
    # also: make them hrs
    # for hr in soup.find_all("p", string="page-break-before"):
    #     hr.name = "hr"
    #     hr.string = ""
    #     _add_class_if_not_exists_to_tag(hr, "page-break-before page-break--hr", "hr")

    for hr in soup.find_all("p", string="page-break-after"):
        hr.name = "hr"
        hr.string = ""
        _add_class_if_not_exists_to_tag(hr, "page-break-after page-break--hr", "hr")

    for hr in soup.find_all("p", string="column-break-before"):
        hr.name = "hr"
        hr.string = ""
        _add_class_if_not_exists_to_tag(hr, "column-break-before page-break--hr", "hr")

    for hr in soup.find_all("p", string="column-break-after"):
        hr.name = "hr"
        hr.string = ""
        _add_class_if_not_exists_to_tag(hr, "column-break-after page-break--hr", "hr")

    return mark_safe(str(soup))
