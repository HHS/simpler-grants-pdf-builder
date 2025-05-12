from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import add_class_to_list

register = template.Library()


@register.filter()
def add_classes_to_lists(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for html_list in soup.find_all(["ul", "ol"]):
        add_class_to_list(html_list)

    return mark_safe(str(soup))
