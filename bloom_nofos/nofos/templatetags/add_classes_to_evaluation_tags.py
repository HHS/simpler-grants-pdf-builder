from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

import re

register = template.Library()


def add_class_if_not_exists_to_tag(element, classname, tag_name=None):
    if classname not in element.get("class", []):
        if tag_name and element.name == tag_name:
            element["class"] = element.get("class", []) + [classname]


@register.filter()
def add_classes_to_evaluation_tags(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    # Look paragraphs that contain a string like "(Maximum points:"
    for p in soup.find_all("p", string=re.compile("\(Maximum points:", re.IGNORECASE)):
        add_class_if_not_exists_to_tag(p, "heading--max-points", "p")
        p["role"] = "heading"
        p["aria-level"] = "7"

    return mark_safe(str(soup))
